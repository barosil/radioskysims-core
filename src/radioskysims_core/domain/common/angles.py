"""
Módulo: src/radioskysims/domain/common/angles.py

Value object ``AngularRange`` (faixa angular em radianos) e o utilitário
``parse_angle`` com o tipo ``AngleInput``.

Extraído de ``domain/common/models.py`` (E7 — quebra por conceito).

Copyright BINGO Collaboration
Last modified: 2026-09-03
"""

from __future__ import annotations

from typing import Any

import astropy.units as u
import numpy as np
from astropy.coordinates import Angle
from pydantic import BaseModel, Field, field_validator, model_validator

from ._lazy import _lazy_import_dask, _lazy_import_xarray


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
