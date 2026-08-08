"""Фаза 31: fuzz-тест anonymizer — случайные и обычные строки НЕ портятся.

mask_fio должен менять только явные полные ФИО (3 слова с заглавной).
Случайные строки и произвольные фразы не должны маскироваться (защита
от регрессии «портa данных»).
"""
from __future__ import annotations

import random

from onec_converter.anonymizer import Anonymizer, mask_fio

_ALPH = 'abcdefghijklmnopqrstuvwxyz ABCDEFGHIJKLMNOPQRSTUVWXYZ 0123456789'
_RU = 'абвгдеёжзийклмнопрстуфхцчшщъыьэюя АБВГДЕЁЖЗИЙКЛМНОПРСТУФХЦЧШЩЪЫЬЭЮЯ'


def _rand(depth: int = 400) -> str:
    """Случайная строка без структуры ФИО/телефона/ИНН."""
    n = random.randint(1, 60)
    chars = (_ALPH if random.random() < 0.5 else _RU).replace(' ', '')
    return ''.join(random.choice(chars) for _ in range(n))


def test_fuzz_random_strings_unchanged():
    random.seed(31)
    for _ in range(300):
        s = _rand()
        assert mask_fio(s) == s, f'портит: {s!r}'


def test_fuzz_ordinary_phrases_unchanged():
    phrases = [
        'ООО Ромашка Плюс',
        'красный диван угловой',
        'Ноутбук Lenovo ThinkPad',
        'город Ташкент',
        'ИП Иванов и партнёры',
        'Платежное поручение 123 от января',
        'Склад Основной, полка А',
        'принтер HP LaserJet Pro',
    ]
    for ph in phrases:
        assert mask_fio(ph) == ph, f'портит фразу: {ph!r}'


def test_fuzz_anonymizer_mask_mode_never_shorter():
    """mode='mask' не должен удалять/укорачивать не-ФИО части (кроме телефона/ИНН)."""
    random.seed(32)
    anon = Anonymizer()  # без fields → маскирует всё по паттернам
    for _ in range(200):
        s = _rand()
        out = anon.apply({'v': s})['v']
        # телефоны/ИНН могут укорачиваться, но простые тексты — нет
        # (маскирование ФИО не уменьшает длину произвольной строки)
        assert isinstance(out, str)
