from __future__ import annotations

import dask.array as da
import xarray as xr
from dask import delayed


def lazy_geometry(provider, tracks, observer) -> xr.Dataset:
    """
    Wrapper lazy para geometria Skyfield
    """

    @delayed
    def _compute():
        return provider.compute(tracks, observer)

    ds = _compute()

    return xr.Dataset(
        {
            k: xr.DataArray(
                da.from_delayed(
                    ds[k],
                    shape=(tracks.time.size,),
                    dtype=float,
                ),
                dims="time",
            )
            for k in ["theta", "range", "az", "el"]
        },
        coords={"time": tracks.time},
    )
