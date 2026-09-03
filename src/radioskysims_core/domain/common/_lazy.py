"""
Módulo: src/radioskysims/domain/common/_lazy.py

Helpers de import tardio (lazy) compartilhados pelos value objects de
``domain/common`` (E7 — quebra de ``models.py`` por conceito).

Copyright BINGO Collaboration
Last modified: 2026-09-03
"""

from __future__ import annotations

import importlib
import importlib.util
from typing import Any

_LAZY_IMPORTS_CACHE: dict[str, Any] = {}


def _module_available(name: str) -> bool:
    """Return True if module `name` can be imported (without importing it)."""
    return importlib.util.find_spec(name) is not None


def _lazy_import_xarray():
    if "xarray" not in _LAZY_IMPORTS_CACHE:
        if not _module_available("xarray"):
            msg = "xarray is required. Install with: pip install xarray"
            raise ImportError(msg)
        _LAZY_IMPORTS_CACHE["xarray"] = importlib.import_module("xarray")
    return _LAZY_IMPORTS_CACHE["xarray"]


def _lazy_import_dask():
    if "dask.array" not in _LAZY_IMPORTS_CACHE:
        if not _module_available("dask"):
            msg = "dask is required. Install with: pip install dask"
            raise ImportError(msg)
        _LAZY_IMPORTS_CACHE["dask.array"] = importlib.import_module("dask.array")
    return _LAZY_IMPORTS_CACHE["dask.array"]


def _lazy_import_astropy_time():
    if "astropy.time" not in _LAZY_IMPORTS_CACHE:
        if not _module_available("astropy.time"):
            msg = "astropy is required. Install with: pip install astropy"
            raise ImportError(msg)
        mod = importlib.import_module("astropy.time")
        _LAZY_IMPORTS_CACHE["astropy.time"] = mod.Time
    return _LAZY_IMPORTS_CACHE["astropy.time"]


def _lazy_import_astropy_location():
    if "astropy.coordinates.EarthLocation" not in _LAZY_IMPORTS_CACHE:
        if not _module_available("astropy.coordinates"):
            msg = "astropy is required. Install with: pip install astropy"
            raise ImportError(msg)
        coords = importlib.import_module("astropy.coordinates")
        _LAZY_IMPORTS_CACHE["astropy.coordinates.EarthLocation"] = coords.EarthLocation
    return _LAZY_IMPORTS_CACHE["astropy.coordinates.EarthLocation"]


def _lazy_import_skyfield():
    """Return tuple (skyfield.load, wgs84, Time class)"""
    if "skyfield" not in _LAZY_IMPORTS_CACHE:
        if not _module_available("skyfield"):
            msg = "skyfield is required. Install with: pip install skyfield"
            raise ImportError(msg)
        sf = importlib.import_module("skyfield.api")
        # skyfield.api exposes load() and wgs84; Time object is created through load().timescale()
        _LAZY_IMPORTS_CACHE["skyfield"] = (sf.load, getattr(sf, "wgs84", None))
    return _LAZY_IMPORTS_CACHE["skyfield"]


def _lazy_import_pandas():
    if "pandas" not in _LAZY_IMPORTS_CACHE:
        if not _module_available("pandas"):
            msg = "pandas is required. Install with: pip install pandas"
            raise ImportError(msg)
        _LAZY_IMPORTS_CACHE["pandas"] = importlib.import_module("pandas")
    return _LAZY_IMPORTS_CACHE["pandas"]
