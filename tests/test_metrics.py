"""Фаза 21: метрики Prometheus."""
from __future__ import annotations

from onec_converter.metrics import Metrics, _sanitize, render_from_timings


def test_render_contains_cache_metrics():
    out = render_from_timings({}, {'files': 3, 'bytes': 100})
    assert 'onec_cache_files 3' in out
    assert 'onec_cache_bytes 100' in out


def test_render_operation_metrics():
    tim = {'read_metadata:Справочник': {'count': 2, 'total_ms': 5, 'max_ms': 3}}
    out = render_from_timings(tim, {})
    assert 'onec_operation_count' in out
    assert '2' in out


def test_sanitize_cyrillic():
    assert _sanitize('read_metadata:Справочник') == 'read_metadata:__________'
    assert _sanitize('read_metadata:ref') == 'read_metadata:ref'


def test_empty_render():
    assert Metrics().render() == '# no metrics'
