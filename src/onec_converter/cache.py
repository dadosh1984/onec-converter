"""Кеш результатов анализа ИБ.

ИБ достигают 2–3 ГБ; повторный парсинг при каждом запросе недопустим.
Ключ кеша — контрольная сумма признаков файла: (путь, размер, mtime_ns,
хэш первых 64 КБ — эвристика для обнаружения изменений при сохранении mtime).
Хранилище: <root>/<hex16>/<name>; root по умолчанию .onec_cache/.
"""

from __future__ import annotations

import hashlib
import json
import re
import shutil
from dataclasses import dataclass
from pathlib import Path

CHUNK = 65536
_SAFE_KEY = re.compile(r'^[a-zA-Z0-9_\-]+$')
_SAFE_NAME = re.compile(r'^[a-zA-Z0-9_\-.]+$')


def _safe_component(value: str, what: str) -> str:
    """Допустимое имя каталога/файла: никаких '/' '/' '..', только буквы/цифры._/-."""
    if not value or '..' in value or '/' in value or '\\' in value:
        raise ValueError(f'недопустимое {what} для кеша: {value!r}')
    pat = _SAFE_NAME if what == 'имя' else _SAFE_KEY
    if not pat.match(value):
        raise ValueError(
            f'недопустимое {what} для кеша: {value!r} '
            '(только [a-zA-Z0-9_.-])')
    return value


def file_key(path: str | Path) -> str:
    """Ключ кеша для файла ИБ: sha256(признаки)."""
    p = Path(path)
    st = p.stat()
    h = hashlib.sha256()
    h.update(str(p.resolve()).encode('utf-8'))
    h.update(str(st.st_size).encode())
    h.update(str(st.st_mtime_ns).encode())
    with p.open('rb') as f:
        h.update(f.read(CHUNK))
    return h.hexdigest()[:16]


@dataclass
class Cache:
    """Простейшее файловое хранилище кеша: ключ -> каталог с именованными артефактами."""

    root: Path = Path('.onec_cache')

    def __post_init__(self) -> None:
        self.root = Path(self.root)
        self.root.mkdir(parents=True, exist_ok=True)

    def _dir(self, key: str) -> Path:
        return self.root / _safe_component(key, 'ключ')

    def has(self, key: str, name: str) -> bool:
        return (self._dir(key) / _safe_component(name, 'имя')).is_file()

    def get(self, key: str, name: str) -> Path | None:
        p = self._dir(key) / _safe_component(name, 'имя')
        return p if p.is_file() else None

    def put(self, key: str, name: str, data: bytes) -> Path:
        d = self._dir(key)
        d.mkdir(parents=True, exist_ok=True)
        p = d / _safe_component(name, 'имя')
        p.write_bytes(data)
        return p

    def put_json(self, key: str, name: str, obj: object) -> Path:
        return self.put(key, name, json.dumps(obj, ensure_ascii=False).encode('utf-8'))

    def get_json(self, key: str, name: str) -> object | None:
        p = self.get(key, name)
        if p is None:
            return None
        data: object = json.loads(p.read_text(encoding='utf-8'))
        return data

    def stats(self) -> dict[str, int]:
        """Статистика кеша: число файлов и общий размер в байтах."""
        files = 0
        total = 0
        if self.root.is_dir():
            for p in self.root.rglob('*'):
                if p.is_file():
                    files += 1
                    total += p.stat().st_size
        return {'files': files, 'bytes': total}

    def clear(self) -> None:
        """Полная очистка кеша."""
        for entry in self.root.iterdir():
            if entry.is_dir():
                shutil.rmtree(entry, ignore_errors=True)
            else:
                entry.unlink(missing_ok=True)
