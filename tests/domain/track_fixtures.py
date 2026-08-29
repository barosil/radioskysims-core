from __future__ import annotations

import dask.array as da
import numpy as np
import pytest
import xarray as xr

from radioskysims_core.domain.tracks.models import Tracks


@pytest.fixture
def numpy_ds():
    sat = 4
    time = 10
    xyz = 3
    positions = np.random.RandomState(0).random_sample((sat, time, xyz))
    ds = xr.Dataset(
        {
            "positions": (("satellite", "time", "xyz"), positions),
            "names": ("satellite", [f"S{i}" for i in range(sat)]),
            "constellation": ("satellite", ["GPS", "GAL", "GPS", "GLO"]),
        },
        coords={
            "satellite": np.arange(sat),
            "time": np.arange(time),
            "xyz": ["x", "y", "z"],
        },
    )
    return Tracks.from_xr(ds)


@pytest.fixture
def dask_ds():
    sat = 4
    time = 100
    xyz = 3
    arr = da.random.random((sat, time, xyz), chunks=(2, 50, 3), seed=42)
    ds = xr.Dataset(
        {
            "positions": (("satellite", "time", "xyz"), arr),
            "names": ("satellite", [f"S{i}" for i in range(sat)]),
            "constellation": ("satellite", ["GPS", "GAL", "GPS", "GLO"]),
        },
        coords={
            "satellite": np.arange(sat),
            "time": np.arange(time),
            "xyz": ["x", "y", "z"],
        },
    )
    return Tracks.from_xr(ds)
