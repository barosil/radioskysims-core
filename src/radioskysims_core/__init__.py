"""
Pacote: radioskysims_core

Kernel compartilhado do RadioSkySim — camada base sem dependência de
pacotes de domínio pesados (beam, skymap, sources, simulation).

Contém:
- config: ConfigPort (ABC) + TomlConfigAdapter (implementação atual)
- db: engine (Database/AsyncDatabase) + base de modelos SQLModel plugável
- logging_config: logging estruturado JSON
- paths: PathManager / resolução da raiz do projeto
- monitor: SystemMonitor (CPU/memória/disco)
- progress: indicador de progresso uniforme
- domain.common: kernel de domínio compartilhado
  (Observer, TimeRange, FrequencyRange, exceptions, ScienceValidator)
- domain.geometry: SkyfieldGeometryProvider, compute_pointing_track
- domain.tracks: TrackFactory
- application.ports.geometry: contrato GeometryProviderPort
- skyfield_loader: loader/cache de efemérides Skyfield

Copyright BINGO Collaboration
"""

from __future__ import annotations

__version__ = "0.1.0"

__all__ = ["__version__"]
