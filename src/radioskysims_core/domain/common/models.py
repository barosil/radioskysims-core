"""
Módulo: src/radioskysims/domain/common/models.py

Re-export dos value objects de ``domain/common`` (E7 — quebra por conceito).

O arquivo monolítico original (~654 l.) foi dividido em:
    - ``frequency.py`` → ``FrequencyRange``
    - ``angles.py``    → ``AngularRange``, ``parse_angle``, ``AngleInput``
    - ``time.py``      → ``TimeRange``
    - ``observer.py``  → ``Observer``
    - ``_lazy.py``     → helpers de import tardio (lazy)

Mantido como shim para compatibilidade retroativa (imports de
``radioskysims_core.domain.common.models``). Novos códigos devem importar
diretamente de ``radioskysims_core.domain.common`` (ou dos sub-módulos).

Copyright BINGO Collaboration
Last modified: 2026-09-03
"""

from __future__ import annotations

from ._lazy import (  # noqa: F401
    _LAZY_IMPORTS_CACHE,
    _lazy_import_astropy_location,
    _lazy_import_astropy_time,
    _lazy_import_dask,
    _lazy_import_pandas,
    _lazy_import_skyfield,
    _lazy_import_xarray,
    _module_available,
)
from .angles import AngleInput, AngularRange, parse_angle  # noqa: F401
from .frequency import FrequencyRange  # noqa: F401
from .observer import Observer  # noqa: F401
from .time import TimeRange  # noqa: F401

__all__ = [
    "AngleInput",
    "AngularRange",
    "FrequencyRange",
    "Observer",
    "TimeRange",
    "parse_angle",
]
