"""
Módulo: src/radioskysims/domain/geometry/interface.py

Descrição:
    Re-export do port canônico GeometryProviderPort como GeometryProvider.

    Mantido para compatibilidade retroativa. O port canônico está em
    ``application/ports/geometry.py``. Novos códigos devem importar
    ``GeometryProviderPort`` diretamente de ``application.ports``.

    Interface para provedores de geometria observacional.
    Define o contrato para cálculo de parâmetros geométricos
    (distância, ângulos, azimute, elevação) entre observador e satélites.
"""

from __future__ import annotations

from radioskysims_core.application.ports.geometry import (
    GeometryProviderPort as GeometryProvider,
)

__all__ = ["GeometryProvider"]
