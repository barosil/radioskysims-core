"""
Módulo: src/radioskysims_core/domain/geometry/skyfield_provider.py

Descrição:
    ⚠️ COMPATIBILIDADE RETROATIVA APENAS
    
    Este módulo foi movido para application/adapters/external_geometry.py
    pois SkyfieldGeometryProvider depende de Skyfield (biblioteca externa),
    não é parte do domínio puro.
    
    Imports aqui são re-export para compatibilidade retroativa com código legado.
    Novos códigos devem importar de:
        from radioskysims_core.application.adapters.external_geometry import (
            SkyfieldGeometryProvider,
        )

Copyright BINGO Collaboration
Last modified: 2026-11-05
"""

from __future__ import annotations

# Re-export para compatibilidade retroativa
from radioskysims_core.application.adapters.external_geometry import (
    SkyfieldGeometryProvider,
)

__all__ = ["SkyfieldGeometryProvider"]
