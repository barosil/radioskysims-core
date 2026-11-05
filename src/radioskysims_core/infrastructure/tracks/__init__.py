"""
Módulo: radioskysims_core/infrastructure/tracks

Descrição:
    Implementações de infraestrutura para tracks de satélites.
    Inclui adaptadores que usam bibliotecas externas (Skyfield, etc).
"""

from radioskysims_core.infrastructure.tracks.track_factory_adapter import (
    TrackFactory,
)

__all__ = ["TrackFactory"]
