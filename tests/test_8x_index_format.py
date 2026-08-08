"""Документирующий тест формата объекта индекса 1CD (Фаза 14, spike).

Запись индекса НЕ реализуется (image-формат не расшифрован). Тест только
ЧИТАЕТ реальную базу 8.1 (read-only) и фиксирует структуру объекта индекса:
page0 — каталог границ листьев (uint32), на хвосте image-страницы — payload
ключа. Поведение append_records не меняется.
"""
from __future__ import annotations

import struct
from pathlib import Path

import pytest

from onec_converter.source_8x_file import Database1CD
from onec_converter.write_8x import _read_object_full

BASE_81 = Path(r'E:/SYSTEM/Desktop/AI_Projects/onec_converter/1C_8.1/1Cv8.1CD')
REQUIRED = pytest.mark.skipif(
    not BASE_81.is_file(),
    reason='реальная база 8.1 отсутствует (read-only)')


@REQUIRED
@pytest.mark.integration
def test_index_object_is_fat_without_objectsig():
    """index_page указывает на FAT-объект БЕЗ сигнатуры '1c fd'.

    Объект индекса — обычный объект данных (fat_level 0/1); первые байты
    данных — каталог границ листьев (uint32), а не сигнатура объекта.
    """
    with Database1CD(BASE_81) as db:
        t = db.tables['_REFERENCE3']
        assert t.index_page, 'у _REFERENCE3 должен быть индекс'
        fl, _, _, data = _read_object_full(BASE_81, t.index_page)
    assert fl in (0, 1)
    # первые байты данных — каталог границ листьев, а не '1c fd'
    assert data[:2] != b'\x1c\xfd'
    # struct of uint32 catalog: monotonically non-decreasing, first == 0
    cat = list(struct.unpack('<16I', data[:64]))
    assert cat[0] == 0
    assert all(l <= r for l, r in zip(cat, cat[1:]) if r != 0)
    assert any(c != 0 for c in cat), 'каталог границ не пуст'


@REQUIRED
@pytest.mark.integration
def test_index_image_tail_has_payload():
    """На хвосте чётной image-страницы индекса лежит payload ключа.

    Документирует, что образы листьев (чётные страницы объекта) хранят
    упакованные ключи в хвосте страницы (битовая дельта-упаковка), а не
    заголовок LeafPageHeader из Tool1CD.
    """
    with Database1CD(BASE_81) as db:
        t = db.tables['_REFERENCE3']
        fl, pages, _, data = _read_object_full(BASE_81, t.index_page)
    n_pages = len(pages)
    assert n_pages >= 3, 'объект индекса должен содержать >=3 страницы изображений'
    # page0 — каталог границ (не используем как image); берём страницу 2 если есть
    assert n_pages >= 3
    page2 = data[2 * 8192:3 * 8192]
    # payload-байты на хвосте страницы (последние ~16 байт) не все нулевые
    tail = page2[-32:]
    assert any(b != 0 for b in tail), f'хвост image-страницы не содержит ключа: {tail.hex()}'
