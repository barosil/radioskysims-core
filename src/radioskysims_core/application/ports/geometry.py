"""
Módulo: src/radioskysims/application/ports/geometry.py

Re-export do port canônico ``GeometryProviderPort`` (definido em
``domain/geometry/interface.py``), mantido para compatibilidade retroativa.
Novos códigos devem importar o contrato de
``radioskysims_core.domain.geometry.interface``.
"""

from __future__ import annotations

from radioskysims_core.domain.geometry.interface import (
    GeometryProviderPort,
)

__all__ = ["GeometryProviderPort"]
