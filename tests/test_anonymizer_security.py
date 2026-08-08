"""Фаза 18: безопасность анонимизатора (ФИО 2-слова/регистр, HMAC)."""
from __future__ import annotations

import pytest

from onec_converter.anonymizer import Anonymizer, _hash_token, mask_fio


@pytest.mark.parametrize('value,expected', [
    ('Иванов Иван Иванович', 'Иванов И. И.'),
    ('Иванов Иван', 'Иванов И.'),          # 2 слова (без отчества) — маскируется
    ('иванов иван иванович', 'иванов и. и.'),  # нижний регистр — маскируется
    ('Пётр Петрович', 'Пётр П.'),
    ('Товар А', 'Товар А'),                 # однобуквенное слово — не ФИО
    ('Петров', 'Петров'),                   # одно слово — без изменений
])
def test_mask_fio_cases(value, expected):
    assert mask_fio(value) == expected


def test_hash_stable_and_secret_dependent():
    a = _hash_token('Иванов', 'KEY')
    b = _hash_token('Иванов', 'KEY')
    c = _hash_token('Иванов', 'OTHER')
    assert a == b and a != c         # стабильно по ключу, зависит от ключа


def test_hash_warns_without_secret():
    import os
    os.environ.pop('ONEC_HASH_SECRET', None)
    with pytest.warns(UserWarning):
        _hash_token('Иванов')


def test_anonymizer_hash_mode():
    os = __import__('os')
    os.environ['ONEC_HASH_SECRET'] = 'test-secret'
    try:
        a = Anonymizer(fields=['Фамилия'], mode='hash')
        out = a.apply({'Фамилия': 'Иванов', 'Имя': 'Иван'})
        assert out['Фамилия'] == _hash_token('Иванов', 'test-secret')
        assert out['Имя'] == 'Иван'  # не в fields — не тронуто
    finally:
        os.environ.pop('ONEC_HASH_SECRET', None)
