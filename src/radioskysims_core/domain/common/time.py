"""
Módulo: src/radioskysims/domain/common/time.py

Value object ``TimeRange`` — intervalo temporal armazenado em JD (UTC),
com conversões para astropy, skyfield, datetime64 e pandas.

Extraído de ``domain/common/models.py`` (E7 — quebra por conceito).

Copyright BINGO Collaboration
Last modified: 2026-09-03
"""

from __future__ import annotations

from typing import Any

import astropy.units as u
import numpy as np
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from ._lazy import (
    _lazy_import_astropy_time,
    _lazy_import_dask,
    _lazy_import_pandas,
    _lazy_import_skyfield,
    _lazy_import_xarray,
)


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
