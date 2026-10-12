"""
Módulo: src/radioskysims/domain/common/frequency.py

Value object ``FrequencyRange`` — faixa de frequências em MHz com
resolução, normalização de unidades e conversões utilitárias.

Extraído de ``domain/common/models.py`` (E7 — quebra por conceito).

Copyright BINGO Collaboration
Last modified: 2026-09-03
"""

from __future__ import annotations

from typing import Any

import astropy.units as u
import numpy as np
from pydantic import BaseModel, Field, field_validator, model_validator

from ._lazy import _lazy_import_dask, _lazy_import_xarray


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
        values = np.arange(
            self.min_mhz, self.max_mhz + self.resolution_mhz, self.resolution_mhz
        )
        # ``np.arange`` pode incluir um ponto extra quando ``(max-min)/res`` é
        # um inteiro exato (ruído de ponto flutuante), ex.: um grid
        # normalizado por ``num_channels`` gera ``num_channels + 1`` pontos.
        # Remove o ponto que fica ~1 resolução acima do máximo.
        if values.size > 1 and (values[-1] - self.max_mhz) >= self.resolution_mhz * 0.999:
            values = values[:-1]
        return values

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
