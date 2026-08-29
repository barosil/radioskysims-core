# tracks/_lazy.py
from __future__ import annotations

import importlib

_xr = None
_np = None
_dask = None


def lazy_xr():
    global _xr  # noqa: PLW0603
    if _xr is None:
        _xr = importlib.import_module("xarray")
    return _xr


def lazy_np():
    global _np  # noqa: PLW0603
    if _np is None:
        _np = importlib.import_module("numpy")
    return _np


def lazy_dask():
    global _dask  # noqa: PLW0603
    if _dask is None:
        _dask = importlib.import_module("dask")
    return _dask
