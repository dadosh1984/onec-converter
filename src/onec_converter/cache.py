"""Кеш результатов анализа ИБ.

ИБ достигают 2–3 ГБ; повторный парсинг при каждом запросе недопустим.
Ключ кеша — контрольная сумма признаков файла: (путь, размер, mtime_ns,
хэш первых 64 КБ — эвристика для обнаружения изменений при сохранении mtime).
Хранилище: <root>/<hex16>/<name>; root по умолчанию .onec_cache/.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path

CHUNK = 65536


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
        return self.root / key

    def has(self, key: str, name: str) -> bool:
        return (self._dir(key) / name).is_file()

    def get(self, key: str, name: str) -> Path | None:
        p = self._dir(key) / name
        return p if p.is_file() else None

    def put(self, key: str, name: str, data: bytes) -> Path:
        d = self._dir(key)
        d.mkdir(parents=True, exist_ok=True)
        p = d / name
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

    def clear(self) -> None:
        """Полная очистка кеша."""
        for entry in self.root.iterdir():
            if entry.is_dir():
                for f in entry.iterdir():
                    f.unlink(missing_ok=True)
                entry.rmdir()
            else:
                entry.unlink(missing_ok=True)
