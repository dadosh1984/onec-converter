"""Фаза 38: мониторинг и DevOps — progress-метрики, S3 multipart."""
from __future__ import annotations

from onec_converter.progress import WorkflowProgress, get_progress, reset_progress


def _s3_module():
    from onec_converter import s3_client as m

    return m


# ---- progress ----
def test_progress_ticks_and_rate():
    p = WorkflowProgress()
    p.tick_rows(5, size=100)
    p.tick_object()
    p.tick_rows(5, size=100)
    p.tick_error()
    s = p.snapshot()
    assert s['rows'] == 10 and s['objects'] == 1
    assert s['errors'] == 1 and s['bytes_moved'] == 200
    assert s['rows_per_sec'] > 0


def test_progress_prometheus_render():
    p = WorkflowProgress()
    p.tick_rows(10)
    out = p.render_prometheus()
    assert 'onec_progress_rows 10' in out
    assert 'onec_progress_objects' in out


def test_progress_global_and_reset():
    from onec_converter.progress import WorkflowProgress
    # Больше нет глобального _active — используем явный объект
    g = WorkflowProgress()
    g.tick_rows(1)
    assert g.rows == 1
    g = WorkflowProgress()
    assert g.rows == 0


# ---- S3 multipart (структура через mock urllib) ----
class Call:
    def __init__(self, method, url, upload_id=''):
        self.method = method
        self.url = url
        self.upload_id = upload_id

    @property
    def headers(self):
        return {'ETag': f'"etag-{self.upload_id}"'}

    def read(self):
        return b'<UploadId>upload-xyz</UploadId>'

    status = 200

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False

    def close(self):
        pass


def _fake_urlopen_factory(log):
    def fake_urlopen(req, timeout=0):
        log.append((req.get_method(), req.full_url))
        if req.get_method() == 'POST' and 'uploads' in req.full_url:
            return Call('POST', req.full_url, 'upload-xyz')
        if req.get_method() == 'PUT':
            return Call('PUT', req.full_url, 'p1')
        # complete
        return Call('POST', req.full_url, 'done')
    return fake_urlopen


def test_multipart_small_delegates_to_put(monkeypatch):
    m = _s3_module()
    monkeypatch.setenv('AWS_ACCESS_KEY_ID', 'ak')
    monkeypatch.setenv('AWS_SECRET_ACCESS_KEY', 'sk')
    monkeypatch.setattr(m.urllib.request, 'urlopen',
                        lambda req, timeout=0: Call('PUT', 'x', 's'))
    rep = m.multipart_upload('b', 'k', b'x' * 10)  # < chunk_size
    assert rep['ok'] is True
    assert rep.get('parts', 1) == 1


def test_multipart_large_sequence(monkeypatch):
    m = _s3_module()
    monkeypatch.setenv('AWS_ACCESS_KEY_ID', 'ak')
    monkeypatch.setenv('AWS_SECRET_ACCESS_KEY', 'sk')
    log: list[tuple[str, str]] = []
    monkeypatch.setattr(m.urllib.request, 'urlopen', _fake_urlopen_factory(log))
    # > chunk_size -> multipart
    rep = m.multipart_upload('b', 'k', b'y' * (6 * 1024 * 1024),
                             chunk_size=5 * 1024 * 1024)
    assert rep['ok'] is True
    methods = [meth for meth, _ in log]
    assert 'POST' in methods and 'PUT' in methods
    assert rep['parts'] >= 2
