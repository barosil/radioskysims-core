from __future__ import annotations

import numpy as np
import pandas as pd
import xarray as xr
from astropy.time import Time

from radioskysims_core.domain.common.models import Observer, TimeRange


def test_from_iso():
    tr = TimeRange.from_iso("2020-01-01T00:00:00", "2020-01-01T01:00:00", resolution=60)
    assert isinstance(tr, TimeRange)
    assert np.isclose(tr.resolution, 60.0)


def test_from_jd():
    t0 = Time("2020-01-01T00:00:00").jd
    t1 = Time("2020-01-01T01:00:00").jd
    tr = TimeRange.from_jd(t0, t1, resolution=120)
    assert tr.min < tr.max
    assert np.isclose(tr.resolution, 120)


def test_from_astropy():
    t0 = Time("2020-01-01T00:00:00")
    t1 = Time("2020-01-01T02:00:00")
    tr = TimeRange.from_astropy(t0, t1, resolution=1800)
    assert tr.start_tai < tr.end_tai
    assert np.isclose(tr.resolution, 1800)


def test_from_config():
    cfg = {
        "start": "2020-01-01T00:00:00",
        "end": "2020-01-01T01:00:00",
        "resolution": 60,
        "unit": "s",
    }
    tr = TimeRange.from_config(cfg)
    assert isinstance(tr, TimeRange)
    assert np.isclose(tr.resolution, 60)


def test_default_resolution():
    t0 = Time("2020-01-01T00:00:00")
    t1 = Time("2020-01-01T00:10:00")
    tr = TimeRange.from_astropy(t0, t1)
    assert np.isclose(tr.resolution, 60.0)


def test_value_array():
    tr = TimeRange.from_iso("2020-01-01T00:00:00", "2020-01-01T00:05:00", resolution=60)
    values = tr.value
    assert isinstance(values, np.ndarray)
    assert len(values) == 6  # inclui o endpoint


def test_to_astropy():
    tr = TimeRange.from_iso("2020-01-01T00:00:00", "2020-01-01T00:03:00", resolution=60)
    times = tr.to_astropy()
    assert isinstance(times, Time)
    assert times.shape[0] == 4


def test_to_datetime64_exact_step():
    from radioskysims.application.services.simulation_service import _compute_time_grid

    tr = TimeRange.from_iso("2026-07-26T00:00:00", "2026-07-26T00:20:00", resolution=600)
    grid = tr.to_datetime64()
    assert grid.dtype == "datetime64[ns]"
    assert len(grid) == 3
    assert np.all(grid.astype("datetime64[s]").astype("datetime64[ns]") == grid)
    assert np.all(np.diff(grid).astype("timedelta64[s]").astype(int) == 600)
    assert np.array_equal(grid, _compute_time_grid(tr))


def test_to_numpy():
    tr = TimeRange.from_iso("2020-01-01T00:00:00", "2020-01-01T00:04:00", resolution=60)
    jd = tr.to_numpy()
    assert isinstance(jd, np.ndarray)
    assert jd.shape[0] == 5


def test_to_pandas():
    tr = TimeRange.from_iso("2020-01-01T00:00:00", "2020-01-01T00:10:00", resolution=300)
    dt_index = tr.to_pandas()
    assert isinstance(dt_index, pd.DatetimeIndex)
    assert len(dt_index) == 3


def test_range_xarray():
    tr = TimeRange.from_iso("2020-01-01T00:00:00", "2020-01-01T00:04:00", resolution=60)
    xr_data = tr.range
    assert isinstance(xr_data, xr.DataArray)
    assert "time" in xr_data.dims
    assert xr_data.attrs["units"] == "TAI seconds"


def test_repr_output():
    tr = TimeRange.from_iso("2020-01-01T00:00:00", "2020-01-01T01:00:00", resolution=60)
    rep = repr(tr)
    assert "TimeRange" in rep
    assert "resolution=" in rep


def test_summary():
    tr = TimeRange.from_iso("2020-01-01T00:00:00", "2020-01-01T00:05:00", resolution=60)
    summary = tr.summary()
    assert summary["entity"] == "TimeRange"
    assert summary["units"]["external"] == "ISO"
    assert summary["is_monotonic"] is True


def test_observer_summary():
    tr = TimeRange.from_iso("2020-01-01T00:00:00", "2020-01-01T00:05:00", resolution=60)
    observer = Observer(lat="-7d13m", lon="-35d52m", height=550.0, timeframe=tr)
    summary = observer.summary()
    assert summary["entity"] == "Observer"
    assert "timeframe" in summary
    assert summary["timeframe"]["entity"] == "TimeRange"
