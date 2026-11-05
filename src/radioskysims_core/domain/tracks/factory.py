"""
Módulo: radioskysims_core/domain/tracks/factory.py

⚠️ DEPRECATED: Este módulo é mantido apenas para backward compatibility.
Nova localização: radioskysims_core.infrastructure.tracks.track_factory_adapter

Use:
    from radioskysims_core.infrastructure.tracks import TrackFactory
"""

from __future__ import annotations

from radioskysims_core.infrastructure.tracks.track_factory_adapter import (  # noqa: F401
    TrackFactory,
)

__all__ = ["TrackFactory"]
