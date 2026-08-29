"""\
Módulo: src/radioskysims/domain/common/models.py

Descrição:
    Value objects e modelos comuns de domínio para faixas físicas, tempo
    e observador, com normalização de unidades e conversões utilitárias.

Copyright BINGO Collaboration
Last modified: 2026-03-03
"""

from __future__ import annotations

import importlib
import importlib.util
from typing import TYPE_CHECKING, Any

# Lightweight imports used immediately
import astropy.units as u
import numpy as np
from astropy.coordinates import Angle
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

# Type hints only for static checking
if TYPE_CHECKING:
    pass  # pragma: no cover

# -----------------------
# Lazy import helpers
# -----------------------
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


# -----------------------
# Models
# -----------------------
class FrequencyRange(BaseModel):
    """Model representing a frequency range (MHz) with resolution."""

    min_mhz: float = Field(..., description="Minimum frequency in MHz")
    max_mhz: float = Field(..., description="Maximum frequency in MHz")
    resolution_mhz: float = Field(..., description="Resolution in MHz")

    @field_validator("min_mhz", "max_mhz", "resolution_mhz", mode="before")
    @classmethod
    def _convert_to_mhz(cls, v):
        if isinstance(v, u.Quantity):
            return v.to(u.MHz).value
        return float(v)

    @model_validator(mode="after")
    def _ensure_resolution(self):
        if self.resolution_mhz == 0.0 and self.min_mhz != self.max_mhz:
            res = (self.max_mhz - self.min_mhz) / 1023
            object.__setattr__(self, "resolution_mhz", res)
        return self

    @classmethod
    def from_floats(
        cls,
        min_val: float,
        max_val: float,
        resolution: float | None = None,
        unit: u.Unit = u.MHz,
    ):
        return cls(
            min_mhz=(min_val * unit).to(u.MHz).value,
            max_mhz=(max_val * unit).to(u.MHz).value,
            resolution_mhz=(resolution * unit).to(u.MHz).value if resolution else 0.0,
        )

    @classmethod
    def from_array(cls, arr: list[float] | np.ndarray | list[u.Quantity]):
        if not isinstance(arr[0], u.Quantity):
            arr = np.asarray(arr) * u.MHz
        else:
            arr = u.Quantity(arr)
            if arr[0].unit != u.MHz:
                arr = arr.to(u.MHz)
        diffs = np.diff(np.sort(arr.value))
        return cls(
            min_mhz=arr.min().value,
            max_mhz=arr.max().value,
            resolution_mhz=float(np.min(diffs)) if len(diffs) > 0 else 0.0,
        )

    @classmethod
    def from_string(cls, s: str, unit: u.Unit = u.MHz):
        parts = list(map(float, s.replace(" ", "").split(",")))
        resolution = parts[2] if len(parts) > 2 else None
        return cls.from_floats(parts[0], parts[1], resolution, unit=unit)

    @classmethod
    def from_config(cls, cfg: dict):
        unit = u.Unit(cfg.get("unit", "MHz"))
        return cls.from_floats(cfg["min"], cfg["max"], cfg.get("resolution"), unit=unit)

    @property
    def value(self) -> np.ndarray:
        if self.resolution_mhz == 0:
            return np.array([self.min_mhz])
        return np.arange(self.min_mhz, self.max_mhz + self.resolution_mhz, self.resolution_mhz)

    @property
    def range(self):
        xr = _lazy_import_xarray()
        da = _lazy_import_dask()
        return xr.DataArray(
            da.from_array(self.value, chunks="auto"),
            dims="frequency",
            name="frequency",
            attrs={"units": "MHz"},
        )

    @property
    def resolution(self) -> float:
        return self.resolution_mhz

    @property
    def min(self) -> float:
        return self.min_mhz

    @property
    def max(self) -> float:
        return self.max_mhz

    def summary(self) -> dict[str, Any]:
        """Retorna resumo estruturado de conformidade e uso de memória."""
        values = self.value
        return {
            "entity": "FrequencyRange",
            "units": "MHz",
            "min_mhz": self.min_mhz,
            "max_mhz": self.max_mhz,
            "resolution_mhz": self.resolution_mhz,
            "num_points": int(values.size),
            "memory_bytes": int(values.nbytes),
            "is_monotonic": bool(np.all(np.diff(values) >= 0)) if values.size > 1 else True,
            "chunks": "auto",
        }


class AngularRange(BaseModel):
    """Model representing angular range in radians."""

    min_rad: float = Field(..., description="Minimum angle in radians")
    max_rad: float = Field(..., description="Maximum angle in radians")
    resolution_rad: float = Field(..., description="Resolution in radians")

    @field_validator("min_rad", "max_rad", "resolution_rad", mode="before")
    @classmethod
    def _convert_to_rad(cls, v):
        if isinstance(v, u.Quantity):
            return v.to(u.rad).value
        return float(v)

    @model_validator(mode="after")
    def _ensure_resolution(self):
        if self.resolution_rad == 0.0 and self.min_rad != self.max_rad:
            res = (1 * u.deg).to(u.rad).value
            object.__setattr__(self, "resolution_rad", res)
        return self

    @classmethod
    def from_floats(
        cls,
        min_val: float,
        max_val: float,
        resolution: float | None = None,
        unit: u.Unit = u.deg,
    ):
        return cls(
            min_rad=(min_val * unit).to(u.rad).value,
            max_rad=(max_val * unit).to(u.rad).value,
            resolution_rad=(resolution * unit).to(u.rad).value if resolution else 0.0,
        )

    @classmethod
    def from_array(cls, arr: list[float] | np.ndarray | list[u.Quantity]):
        if not isinstance(arr[0], u.Quantity):
            arr = np.asarray(arr) * u.deg
        else:
            arr = u.Quantity(arr)
            if arr[0].unit != u.deg:
                arr = arr.to(u.deg)
        arr = arr.to(u.rad)
        diffs = np.diff(np.sort(arr.value))
        return cls(
            min_rad=arr.min().value,
            max_rad=arr.max().value,
            resolution_rad=float(np.min(diffs)) if len(diffs) > 0 else 0.0,
        )

    @classmethod
    def from_string(cls, s: str, unit: u.Unit = u.deg):
        parts = list(map(float, s.replace(" ", "").split(",")))
        resolution = parts[2] if len(parts) > 2 else None
        return cls.from_floats(parts[0], parts[1], resolution, unit=unit)

    @classmethod
    def from_degrees(cls, min_val: float, max_val: float, resolution: float | None = None):
        return cls.from_floats(min_val, max_val, resolution, unit=u.deg)

    @classmethod
    def from_hours(cls, min_val: float, max_val: float, resolution: float | None = None):
        return cls.from_floats(min_val, max_val, resolution, unit=u.hourangle)

    @classmethod
    def from_config(cls, cfg: dict):
        unit = u.Unit(cfg.get("unit", "deg"))
        return cls.from_floats(cfg["min"], cfg["max"], cfg.get("resolution"), unit=unit)

    @property
    def value(self) -> np.ndarray:
        if self.resolution_rad == 0:
            return np.array([self.min_rad])
        return np.arange(self.min_rad, self.max_rad + self.resolution_rad / 2, self.resolution_rad)

    @property
    def range(self):
        xr = _lazy_import_xarray()
        da = _lazy_import_dask()
        values = self.value
        return xr.DataArray(
            da.from_array(values, chunks="auto"),
            dims="angle",
            name="angle",
            attrs={
                "units": "rad",
                "min_deg": Angle(self.min_rad * u.rad).degree,
                "max_deg": Angle(self.max_rad * u.rad).degree,
                "resolution_deg": Angle(self.resolution_rad * u.rad).degree,
                "min_hms": Angle(self.min_rad * u.rad).to_string(
                    unit=u.hourangle, sep=":", precision=2
                ),
                "max_hms": Angle(self.max_rad * u.rad).to_string(
                    unit=u.hourangle, sep=":", precision=2
                ),
            },
        )

    @property
    def angle(self) -> Angle:
        return Angle(self.value * u.rad)

    @property
    def resolution(self) -> float:
        return self.resolution_rad

    @property
    def min(self) -> float:
        return self.min_rad

    @property
    def max(self) -> float:
        return self.max_rad

    def __repr__(self) -> str:
        min_deg = Angle(self.min_rad * u.rad).degree
        max_deg = Angle(self.max_rad * u.rad).degree
        res_deg = Angle(self.resolution_rad * u.rad).degree
        return f"AngularRange({min_deg:.2f}° → {max_deg:.2f}°, Δ = {res_deg:.2f}°)"

    def summary(self) -> dict[str, Any]:
        """Retorna resumo estruturado de conformidade e uso de memória."""
        values = self.value
        return {
            "entity": "AngularRange",
            "units": {"external": "deg", "internal": "rad"},
            "min_rad": self.min_rad,
            "max_rad": self.max_rad,
            "resolution_rad": self.resolution_rad,
            "min_deg": float(Angle(self.min_rad * u.rad).degree),
            "max_deg": float(Angle(self.max_rad * u.rad).degree),
            "num_points": int(values.size),
            "memory_bytes": int(values.nbytes),
            "is_monotonic": bool(np.all(np.diff(values) >= 0)) if values.size > 1 else True,
            "chunks": "auto",
        }


class TimeRange(BaseModel):
    """TimeRange stored internally in JD. Accepts astropy Time, skyfield times, strings, floats or config."""

    model_config = ConfigDict(arbitrary_types_allowed=True)

    start_jd: float = Field(..., description="Start JD")
    end_jd: float = Field(..., description="End JD")
    resolution_sec: float = Field(..., description="Resolution in seconds")

    @field_validator("start_jd", "end_jd", mode="before")
    @classmethod
    def _convert_to_jd(cls, v):
        Time = _lazy_import_astropy_time()
        if isinstance(v, Time):
            return float(v.jd)
        if isinstance(v, str):
            return float(Time(v).jd)
        return float(v)

    @field_validator("resolution_sec", mode="before")
    @classmethod
    def _convert_resolution(cls, v):
        if isinstance(v, u.Quantity):
            return v.to_value(u.s)
        return float(v)

    @model_validator(mode="after")
    def _ensure_resolution(self) -> TimeRange:
        if self.resolution_sec == 0.0:
            object.__setattr__(self, "resolution_sec", 60.0)
        return self

    @classmethod
    def from_astropy(cls, start, end, resolution: float | None = None, unit: u.Unit = u.s):
        return cls(
            start_jd=float(start.jd),
            end_jd=float(end.jd),
            resolution_sec=(resolution * unit).to_value(u.s) if resolution else 0.0,
        )

    @classmethod
    def from_iso(cls, start: str, end: str, resolution: float | None = None, unit: u.Unit = u.s):
        Time = _lazy_import_astropy_time()
        return cls.from_astropy(Time(start), Time(end), resolution, unit)

    @classmethod
    def from_jd(
        cls,
        start_jd: float,
        end_jd: float,
        resolution: float | None = None,
        unit: u.Unit = u.s,
    ):
        Time = _lazy_import_astropy_time()
        return cls.from_astropy(
            Time(start_jd, format="jd"), Time(end_jd, format="jd"), resolution, unit
        )

    @classmethod
    def from_config(cls, cfg: dict):
        Time = _lazy_import_astropy_time()
        unit = u.Unit(cfg.get("unit", "s"))
        start = Time(cfg["start"])
        end = Time(cfg["end"])
        resolution = cfg.get("resolution")
        return cls.from_astropy(start, end, resolution, unit)

    @property
    def value(self) -> np.ndarray:
        _res_jd = self.resolution_sec / (24 * 60 * 60)
        if _res_jd <= 0:
            return np.array([self.start_jd, self.end_jd])
        n_steps = int(np.round((self.end_jd - self.start_jd) / _res_jd)) + 1
        return self.start_jd + np.arange(n_steps, dtype=float) * _res_jd

    @property
    def range(self):
        xr = _lazy_import_xarray()
        da = _lazy_import_dask()
        _res_jd = self.resolution_sec / (24 * 60 * 60)
        if _res_jd <= 0:
            _range = np.array([self.start_jd, self.end_jd])
            return xr.DataArray(_range, dims="time", name="time", attrs={"units": "TAI seconds"})
        n_steps = int(np.round((self.end_jd - self.start_jd) / _res_jd)) + 1
        _range = da.linspace(self.start_jd, self.end_jd, n_steps, endpoint=True)
        return xr.DataArray(_range, dims="time", name="time", attrs={"units": "TAI seconds"})

    @property
    def start_tai(self) -> float:
        """TAI seconds equivalent of start_jd."""
        return self.start_jd

    @property
    def end_tai(self) -> float:
        """TAI seconds equivalent of end_jd."""
        return self.end_jd

    def to_astropy(self):
        Time = _lazy_import_astropy_time()
        return Time(self.value, format="jd")

    def to_datetime64(self) -> np.ndarray:
        """Retorna um array ``datetime64[ns]`` com passos exatos de resolution_sec."""
        Time = _lazy_import_astropy_time()
        start = Time(self.start_jd, format="jd").utc.datetime64.astype("datetime64[ns]")
        if self.resolution_sec <= 0:
            return np.array([start], dtype="datetime64[ns]")

        n_steps = int(np.round((self.end_jd - self.start_jd) / (self.resolution_sec / 86400.0))) + 1
        step_ns = np.timedelta64(int(round(self.resolution_sec * 1e9)), "ns")
        return start + np.arange(n_steps, dtype=np.int64) * step_ns

    def to_numpy(self) -> np.ndarray:
        return self.to_astropy().utc.jd

    def to_pandas(self):
        pd = _lazy_import_pandas()
        return pd.to_datetime(self.to_datetime64())

    def to_skyfield(self):
        skyfield_load, _ = _lazy_import_skyfield()
        ts = skyfield_load.timescale()
        # Converte UTC JD → TT JD antes de passar ao skyfield.
        # Os JDs internos estão em escala UTC, mas ts.tt_jd espera TT.
        Time = _lazy_import_astropy_time()
        tt_jd = Time(self.value, format="jd").tt.jd
        return ts.tt_jd(tt_jd)

    def to_tuple(self):
        Time = _lazy_import_astropy_time()
        start = Time(self.start_jd, format="jd")
        end = Time(self.end_jd, format="jd")
        return (start, end, self.resolution_sec)

    def slice(self, interval_days: float) -> list[TimeRange]:
        if interval_days <= 0:
            msg = "Interval must be > 0"
            raise ValueError(msg)
        starts = np.arange(self.start_jd, self.end_jd, interval_days)
        ends = np.append(starts[1:], self.end_jd)
        return [
            TimeRange(start_jd=float(s), end_jd=float(e), resolution_sec=self.resolution_sec)
            for s, e in zip(starts, ends, strict=False)
        ]

    @property
    def min(self) -> float:
        return self.start_jd

    @property
    def max(self) -> float:
        return self.end_jd

    @property
    def resolution(self) -> float:
        return self.resolution_sec

    def __repr__(self) -> str:
        Time = _lazy_import_astropy_time()
        start_str = Time(self.start_jd, format="jd").iso
        end_str = Time(self.end_jd, format="jd").iso
        return f"<TimeRange {start_str} to {end_str} | resolution={self.resolution_sec:.1f}s>"

    def summary(self) -> dict[str, Any]:
        """Retorna resumo estruturado de conformidade temporal e memória."""
        values = self.value
        return {
            "entity": "TimeRange",
            "units": {"external": "ISO", "internal": "MJD/JD", "resolution": "s"},
            "start_jd": self.start_jd,
            "end_jd": self.end_jd,
            "resolution_sec": self.resolution_sec,
            "num_points": int(values.size),
            "memory_bytes": int(values.nbytes),
            "is_monotonic": bool(np.all(np.diff(values) >= 0)) if values.size > 1 else True,
            "chunks": "auto",
            "timezone": "UTC",
        }


AngleInput = str | tuple | list | float | int | u.Quantity | Angle


def parse_angle(value: AngleInput, default_unit=u.deg) -> Angle:
    """Convert input into an astropy.coordinates.Angle object."""
    if isinstance(value, Angle):
        return value
    if isinstance(value, u.Quantity):
        return Angle(value)
    if isinstance(value, int | float):
        return Angle(value, unit=default_unit)
    if isinstance(value, tuple | list):
        # accepts (deg, min, sec) or (deg, min) or (deg,)
        sign = -1 if value[0] < 0 else 1
        abs_values = [abs(v) for v in value]
        if len(abs_values) == 3:
            angle = abs_values[0] + abs_values[1] / 60 + abs_values[2] / 3600
        elif len(abs_values) == 2:
            angle = abs_values[0] + abs_values[1] / 60
        elif len(abs_values) == 1:
            angle = abs_values[0]
        else:
            msg = "Tuple/list angle must have up to 3 elements"
            raise ValueError(msg)
        return Angle(sign * angle, unit=default_unit)
    if isinstance(value, str):
        try:
            return Angle(value)
        except Exception as e:
            msg = f"Invalid angle string: {value}"
            raise ValueError(msg) from e
    msg = f"Invalid angle format: {value}"
    raise TypeError(msg)


class Observer(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)

    lat: AngleInput
    lon: AngleInput
    height: float | u.Quantity | None = 0.0  # meters
    timeframe: TimeRange

    @field_validator("lat")
    @classmethod
    def validate_lat(cls, v):
        angle = parse_angle(v, default_unit=u.deg)
        deg = angle.to_value(u.deg)
        if not -90 <= deg <= 90:
            msg = "Latitude must be between -90 and 90 degrees"
            raise ValueError(msg)
        return angle.to(u.deg)

    @field_validator("lon")
    @classmethod
    def validate_lon(cls, v):
        angle = parse_angle(v, default_unit=u.deg)
        deg = angle.to_value(u.deg)
        if not -180 <= deg <= 360:
            msg = "Longitude must be between -180 and 360 degrees"
            raise ValueError(msg)
        return angle.to(u.deg)

    @field_validator("height")
    @classmethod
    def validate_height(cls, v):
        if isinstance(v, u.Quantity):
            return v.to(u.m)
        return v * u.m

    def to_astropy(self):
        EarthLocation = _lazy_import_astropy_location()
        return (
            EarthLocation(lat=self.lat, lon=self.lon, height=self.height),
            self.timeframe.to_astropy(),
        )

    def to_skyfield(self):
        _, wgs84 = _lazy_import_skyfield()
        location = wgs84.latlon(
            latitude_degrees=self.lat.to_value(u.deg),
            longitude_degrees=self.lon.to_value(u.deg),
            elevation_m=self.height.to_value(u.m),
        )
        return location, self.timeframe.to_skyfield()

    def summary(self) -> dict[str, Any]:
        """Retorna resumo estruturado do observador e da janela temporal."""
        return {
            "entity": "Observer",
            "lat_deg": float(self.lat.to_value(u.deg)),
            "lon_deg": float(self.lon.to_value(u.deg)),
            "height_m": float(self.height.to_value(u.m)),
            "timeframe": self.timeframe.summary(),
            "units": {
                "angles_external": "deg",
                "angles_internal": "rad",
                "time_internal": "MJD/JD",
            },
        }
