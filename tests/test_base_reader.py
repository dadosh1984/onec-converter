"""Unit-тесты base_reader."""
from pathlib import Path

import pytest

from onec_converter.base_reader import Base77, BaseError
from tests.fixtures.gen_dat import make_dat


def test_base77_requires_files(tmp_path: Path):
    with pytest.raises(BaseError):
        Base77(tmp_path)


def test_base77_opens_real_like_dir(tmp_path: Path):
    (tmp_path / '1Cv7.MD').write_bytes(b'd0cf11e0')
    (tmp_path / '1Cv77.dat').write_bytes(make_dat(unique_ids={1: 2}))
    base = Base77(tmp_path)
    assert base.data.unique_ids() == {1: 2}
    base.close()


def test_from_dt_roundtrip(tmp_path: Path):
    import zlib
    dat = make_dat(unique_ids={1: 5})
    dt = tmp_path / '1Cv7.DT'
    dt.write_bytes(zlib.compress(dat))
    base = Base77.from_dt(dt, workdir=tmp_path / 'work')
    assert base.data.unique_ids() == {1: 5}
    base.close()
