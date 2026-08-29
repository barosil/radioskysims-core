# domain/common/__init__.py
from __future__ import annotations

from .exceptions import (
    BeamRepositoryError,
    CommonSkyMapError,
    DomainError,
    SatelliteError,
    TrackError,
)
from .models import AngularRange, FrequencyRange, Observer, TimeRange
from .science_validator import ScienceValidator

__all__ = [
    "AngularRange",
    "BeamRepositoryError",
    "CommonSkyMapError",
    "DomainError",
    "FrequencyRange",
    "Observer",
    "SatelliteError",
    "ScienceValidator",
    "TimeRange",
    "TrackError",
]


def __getattr__(name: str):
    if name in {
        "BeamRepositoryError",
        "CommonSkyMapError",
        "DomainError",
        "SatelliteError",
        "SkyMapError",
        "TrackError",
    }:
        from . import exceptions

        return getattr(exceptions, name)

    if name in {"AngularRange", "FrequencyRange", "Observer", "TimeRange"}:
        from . import models

        return getattr(models, name)

    if name == "ScienceValidator":
        from .science_validator import ScienceValidator

        return ScienceValidator

    msg = f"module {__name__!r} has no attribute {name!r}"
    raise AttributeError(msg)
