"""Тесты коннектора .dt (8.x)."""
import pytest

from onec_converter.source_8x_dt import DtFormatError, open_dt


def test_open_dt_not_implemented(tmp_path):
    with pytest.raises(DtFormatError):
        open_dt(tmp_path / 'x.dt')
