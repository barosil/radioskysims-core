"""
Exceções comuns do domínio do projeto RadioSkySim.
"""

from __future__ import annotations


class DomainError(Exception):
    """Exceção base para erros de domínio."""


# SkyMapError vive no pacote ``radioskysims-skymap`` (Fase 3). Até lá,
# usamos um fallback local — sem dependência do núcleo com o pacote de skymap.
try:
    from radioskysims_skymap.domain.skymap.exceptions import SkyMapError as SkyMapError
except Exception:

    class SkyMapError(DomainError):
        """Exceção levantada quando há erro ao manipular SkyMap."""


class BeamRepositoryError(DomainError):
    """Exceção levantada quando há erro ao manipular repositório de Beam."""


class CommonSkyMapError(DomainError):
    """Exceção comum levantada quando há erro ao manipular SkyMap."""


class SatelliteError(DomainError):
    """Exceção levantada quando há erro ao manipular satélites."""


class TrackError(DomainError):
    """Exceção levantada quando há erro ao manipular tracks."""
