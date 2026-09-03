"""
Módulo: src/radioskysims/domain/common/observer.py

Value object ``Observer`` — observador terrestre (lat/lon/altura) com uma
janela temporal (``TimeRange``) e conversões astropy/skyfield.

Extraído de ``domain/common/models.py`` (E7 — quebra por conceito).

Copyright BINGO Collaboration
Last modified: 2026-09-03
"""

from __future__ import annotations

from typing import Any

import astropy.units as u
from pydantic import BaseModel, ConfigDict, field_validator

from ._lazy import _lazy_import_astropy_location, _lazy_import_skyfield
from .angles import AngleInput, parse_angle
from .time import TimeRange


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

    def view(self):
        """Retorna uma visão interativa (holoviews) do observador.

        Renderiza um mapa com tiles OSM e a localização do observador.
        O import de ``radioskysims-viz`` é lazy (mesmo padrão do
        ``config_loader``), mantendo o núcleo importável sem visualização.

        Exemplo (notebook)::

            uirapuru.observer.view()  # mapa interativo

        Returns:
            ``hv.Overlay`` (tiles * pontos) quando ``radioskysims-viz``
            estiver disponível.

        Raises:
            ImportError: Se ``radioskysims-viz``/holoviews não estiverem
                instalados.
        """
        try:
            from radioskysims_viz.radiotelescope import observer_map
        except ImportError as exc:  # pragma: no cover - ambiente sem viz
            msg = (
                "Observer.view() requer 'radioskysims-viz' (holoviews). "
                "Instale com: uv sync --extra viz (ou --extra all)."
            )
            raise ImportError(msg) from exc
        return observer_map(self)
