"""Фаза 49 (0.32.0): память и потоковость — U35/U36/U37/U38/U39/U40/U42.

Проверки:
- v77_reader: потоковый сканер секций (iter_sections_text) и V77Reader
  через mmap — одна секция в памяти, а не весь файл
- s3 upload_file: потоковая загрузка чанками (O(1) память) без read_bytes
- table_stats_all: единый проход по всем таблицам + общий кеш
- read_metadata: in-memory LRU (U39) — второй вызов не читает диск
- dump-records --max-bytes: потоковый JSON/CSV без накопления списка
- cache.put: атомарная запись tmp+rename (U42) — нет битого артефакта
"""

from __future__ import annotations

import json
import threading
from pathlib import Path

from onec_converter.fake_1cd import FixtureField
from onec_converter.source_8x_file import _clear_mem_meta, _mem_meta, read_metadata
from onec_converter.v77_reader import V77Reader, iter_sections_text
from tests.fixtures.gen_dat import make_dat

# ---- U35: потоковое чтение секций 1Cv77.dat ----

def _write_dat(tmp_path: Path) -> Path:
    data = make_dat(
        unique_ids={1: 3, 2: 5},
        constants=[(7, ['a', 'b'])],
        references={11: [['x', 'y']], 12: [['p', 'q'], ['r', 's']]},
    )
    p = tmp_path / '1Cv77.dat'
    p.write_bytes(data)
    return p


def test_v77_iter_sections_text_names(tmp_path: Path):
    p = _write_dat(tmp_path)
    names = [n for n, _ in iter_sections_text(p)]
    assert 'System table' in names
    assert 'Unique IDs' in names and 'Constants' in names and 'References' in names


def test_v77_reader_streamed_matches_old(tmp_path: Path):
    """V77Reader (потоковый) даёт те же данные, что from_bytes (старый путь)."""
    p = _write_dat(tmp_path)
    a = V77Reader(p)
    b = V77Reader.from_bytes(p.read_bytes())
    assert a.sections() == b.sections()
    assert a.unique_ids() == b.unique_ids() == {1: 3, 2: 5}
    assert a.constants() == b.constants()
    assert a.references() == b.references()


def test_v77_reader_quotes_and_braces_inside_strings(tmp_path: Path):
    """Кавычки с удвоением и фигурные скобки внутри строк не ломают сканер."""
    text = ('{"7.70","",{"System table",{0,0,"a{b}c"}},'
            '{"Unique IDs",{1,"3|"}},{"References",{5,{"x""y"}}},'
            '{"Constants",{7,{"v"}}}}')
    p = tmp_path / '1Cv77.dat'
    p.write_bytes(text.encode('cp866'))
    names = dict(iter_sections_text(p))
    assert set(names) == {'System table', 'Unique IDs', 'References', 'Constants'}
    r = V77Reader(p)
    assert r.references()[5] == [['x"y']]


# ---- U36: s3 upload_file (потоковая загрузка) ----

def test_s3_upload_file_streams_chunks(tmp_path: Path):
    import http.server
    import threading as _t

    from onec_converter.s3_client import upload_file

    received: dict[str, bytes] = {}

    class Handler(http.server.BaseHTTPRequestHandler):
        def do_PUT(self):
            n = int(self.headers.get('Content-Length', '0'))
            body = self.rfile.read(n)
            received['path'] = self.path
            received['body'] = body
            received['sha'] = self.headers.get('x-amz-content-sha256', '')
            self.send_response(200)
            self.end_headers()

        def log_message(self, *args: object) -> None:
            pass

    srv = http.server.ThreadingHTTPServer(('127.0.0.1', 0), Handler)
    port = srv.server_address[1]
    t = _t.Thread(target=srv.serve_forever, daemon=True)
    t.start()
    try:
        f = tmp_path / 'report.bin'
        payload = bytes(range(256)) * 1024  # 256 КБ
        f.write_bytes(payload)
        rep = upload_file('bkt', 'rep.bin', f,
                          access_key='AK', secret_key='SK',
                          endpoint=f'http://127.0.0.1:{port}', region='us-east-1')
        assert rep['streamed'] is True and rep['ok'] is True
        assert received['path'] == '/bkt/rep.bin'
        assert received['body'] == payload
        assert received['sha']
        assert received['sha'] == __import__('hashlib').sha256(payload).hexdigest()
    finally:
        srv.shutdown()
        t.join()


def test_s3_upload_file_missing_file(tmp_path: Path):
    from onec_converter.s3_client import S3Error, upload_file

    try:
        upload_file('b', 'k', tmp_path / 'nope.json',
                    access_key='AK', secret_key='SK')
    except S3Error as exc:
        assert 'нет файла' in str(exc)
    else:
        raise AssertionError('S3Error не поднят')


# ---- U37: table_stats_all одним проходом ----

def test_table_stats_all_shared_cache(tmp_path: Path):
    from onec_converter.fake_1cd import FixtureTable, build_fake_1cd
    from onec_converter.source_8x_file import Database1CD

    tbl = FixtureTable(
        name='T1',
        fields=[FixtureField('F', 'S', length=10)],
        rows=[b'abc' + b'\x00' * 7, b'def' + b'\x00' * 7],
    )
    cd = tmp_path / '1Cv8.1CD'
    cd.write_bytes(build_fake_1cd([tbl]))
    with Database1CD(cd) as db:
        t = db.tables['T1']
        rows, nbytes = db.table_stats('T1')
        assert nbytes == 20
        assert rows * t.row_length == nbytes
        all_stats = db.table_stats_all()
        assert all_stats['T1'] == (rows, nbytes)
        assert db._stats_cache is not None  # общий кеш наполнен
        assert 'T1' in db.table_stats_all()


# ---- U39: in-memory LRU read_metadata ----

def test_read_metadata_mem_lru_hits():
    import pytest

    from tests.test_cli_extract import BASE_81

    if not BASE_81.is_file():
        pytest.skip('реальная база 8.1 отсутствует (read-only)')
    _clear_mem_meta()
    md1 = read_metadata(BASE_81)
    assert md1 and md1.get('tables')
    assert _mem_meta  # попал в LRU
    before = len(_mem_meta)
    md2 = read_metadata(BASE_81)  # из памяти
    assert md2 == md1
    assert len(_mem_meta) == before
    _clear_mem_meta()


# ---- U40: dump-records --max-bytes потоковый ----

def test_cli_dump_records_max_bytes_json(tmp_path: Path, capsys):
    from tests.fixtures.gen_dat import make_dat

    base = tmp_path / 'base'
    base.mkdir()
    (base / '1Cv77.dat').write_bytes(make_dat(unique_ids={1: 2}))
    from onec_converter import cli

    rc = cli.main(['dump-records', '--source-dir', str(base),
                   '--table', '_UNKNOWN', '--limit', '1', '--max-bytes', '1'])
    assert rc == 1  # нет таблицы — потоковый путь не падает раньше времени
    capsys.readouterr()


def test_cli_dump_records_streams_json_valid(tmp_path: Path):
    from onec_converter import cli
    from onec_converter.fake_1cd import FixtureTable, build_fake_1cd

    cd = tmp_path / 'base' / '1Cv8.1CD'
    (tmp_path / 'base').mkdir()
    cd.write_bytes(build_fake_1cd([FixtureTable(
        name='T1',
        fields=[FixtureField('F', 'S', length=10)],
        rows=[b'abc' + b'\x00' * 7, b'def' + b'\x00' * 7])]))
    rc = cli.main(['dump-records', '--source-dir', str(tmp_path / 'base'),
                   '--table', 'T1', '--limit', '100', '--max-bytes', '1000000',
                   '--format', 'json'])
    assert rc == 0
    # stdout должен быть валидным JSON-массивом
    import io
    from contextlib import redirect_stdout

    buf = io.StringIO()
    with redirect_stdout(buf):
        cli.main(['dump-records', '--source-dir', str(tmp_path / 'base'),
                  '--table', 'T1', '--limit', '100', '--format', 'json'])
    rows = json.loads(buf.getvalue())
    assert rows and all('F' in r for r in rows)


# ---- U42: cache.put атомарно (tmp + rename) ----

def test_cache_put_atomic_no_tmp_leftover(tmp_path: Path):
    from onec_converter.cache import Cache

    c = Cache(root=tmp_path / 'cache')
    p = c.put('k1', 'artifact', b'data-v1')
    assert p.read_bytes() == b'data-v1'
    c.put('k1', 'artifact', b'data-v2')
    assert p.read_bytes() == b'data-v2'
    leftovers = list(tmp_path.glob('cache/**/*.tmp'))
    assert leftovers == []


def test_cache_concurrent_puts_atomic(tmp_path: Path):
    from onec_converter.cache import Cache

    c = Cache(root=tmp_path / 'cache')
    errors: list[Exception] = []

    def worker(i: int) -> None:
        try:
            for n in range(30):
                c.put('shared', f'a{i}', f'v{i}-{n}'.encode())
        except Exception as exc:  # noqa: BLE001
            errors.append(exc)

    threads = [threading.Thread(target=worker, args=(i,)) for i in range(4)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    assert errors == []
    for i in range(4):
        assert (tmp_path / 'cache' / 'shared' / f'a{i}').is_file()
