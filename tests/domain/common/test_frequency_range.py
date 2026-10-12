from __future__ import annotations

import numpy as np
import xarray as xr
from astropy import units as u

from radioskysims_core.domain.common.models import FrequencyRange


def test_from_floats():
    fr = FrequencyRange.from_floats(100, 200, 10)
    assert fr.min == 100.0
    assert fr.max == 200.0
    assert fr.resolution == 10.0


def test_from_floats_with_unit():
    fr = FrequencyRange.from_floats(1e8, 2e8, 1e7, unit=u.Hz)
    assert np.isclose(fr.min, 100.0)
    assert np.isclose(fr.max, 200.0)
    assert np.isclose(fr.resolution, 10.0)


def test_from_array_without_units():
    arr = np.linspace(100, 200, 11)
    fr = FrequencyRange.from_array(arr)
    assert np.isclose(fr.min, 100.0)
    assert np.isclose(fr.max, 200.0)
    assert np.isclose(fr.resolution, 10.0)


def test_from_array_with_units():
    arr = [100 * u.MHz, 110 * u.MHz, 120 * u.MHz]
    fr = FrequencyRange.from_array(arr)
    assert fr.resolution == 10.0


def test_from_string():
    fr = FrequencyRange.from_string("100,200,10")
    assert fr.min == 100.0
    assert fr.max == 200.0
    assert fr.resolution == 10.0


def test_from_config():
    cfg = {"min": 100, "max": 200, "resolution": 10, "unit": "MHz"}
    fr = FrequencyRange.from_config(cfg)
    assert fr.min == 100.0
    assert fr.max == 200.0
    assert fr.resolution == 10.0


def test_default_resolution():
    fr = FrequencyRange.from_floats(100, 200)
    assert len(fr.value) == 1024
    assert np.isclose(fr.resolution, (200 - 100) / 1023)


def test_range_and_value():
    fr = FrequencyRange.from_floats(100, 200, 10)
    assert isinstance(fr.range, xr.DataArray)
    assert fr.range.attrs["units"] == "MHz"
    assert np.allclose(fr.value, np.arange(100, 201, 10))


def test_value_no_off_by_one_when_span_is_exact_multiple():
    """Regressão: grid normalizado por ``num_channels`` não gera n+1 pontos.

    ``FrequencyRange.from_floats(min, max, (max-min)/(n-1))`` (usado pela
    normalização por canais) produzia ``n + 1`` pontos por ruído de ponto
    flutuante no ``np.arange`` inclusivo.
    """
    n = 4096
    res = (1245.0 - 995.0) / (n - 1)
    fr = FrequencyRange.from_floats(995.0, 1245.0, res)

    assert len(fr.value) == n
    assert np.isclose(fr.value[0], 995.0)
    assert np.isclose(fr.value[-1], 1245.0)


def test_summary():
    fr = FrequencyRange.from_floats(100, 110, 5)
    summary = fr.summary()
    assert summary["entity"] == "FrequencyRange"
    assert summary["units"] == "MHz"
    assert summary["num_points"] == 3
    assert summary["is_monotonic"] is True
