from __future__ import annotations

import os
import tempfile

import numpy as np
import pytest


def test_structure_validation(numpy_ds):
    s = numpy_ds
    assert set(s.dataset.sizes) >= {"satellite", "time", "xyz"}
    assert "positions" in s.dataset
    assert s.dataset["positions"].shape == (4, 10, 3)


def test_filters(numpy_ds):
    s = numpy_ds
    gps = s.filter_by_constellation("GPS")
    assert gps.dataset.sizes["satellite"] == 2

    t2 = s.filter_by_time(start=2, end=5)
    assert t2.dataset.sizes["time"] == 4

    only0 = s.filter_by_satellite(0)
    assert only0.dataset.sizes["satellite"] == 1


def test_get_chunks_info_dask(dask_ds):
    info = dask_ds.get_chunks_info("positions")
    assert info["chunks"] is not None
    assert info["num_chunk_grid"][0] >= 1


def test_get_chunks_numpy(numpy_ds):
    chunks = numpy_ds.get_chunks("positions")
    ((idx, arr),) = tuple(chunks.items())
    assert isinstance(idx, tuple)
    assert arr.shape == (4, 10, 3)


def test_get_chunks_dask(dask_ds):
    chunks = dask_ds.get_chunks("positions", max_chunks=2)
    assert len(chunks) == 2
    for arr in chunks.values():
        assert isinstance(arr, np.ndarray)


def test_memory_limit(dask_ds):
    with pytest.raises(MemoryError):
        # set absurdly low total limit to force MemoryError
        dask_ds.get_chunks("positions", max_chunks=10, max_total_bytes=1)


def test_exports(numpy_ds):
    with tempfile.TemporaryDirectory() as tmp:
        zpath = os.path.join(tmp, "out.zarr")
        numpy_ds.to_zarr(zpath)
        assert os.path.exists(zpath)
        h5path = os.path.join(tmp, "out.nc")
        numpy_ds.to_hdf5(h5path)
        assert os.path.exists(h5path)
