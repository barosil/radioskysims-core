"""
Módulo: src/radioskysims_core/application/adapters/__init__.py

Descrição:
    Adapters: implementações de ports que dependem de bibliotecas externas.
    Aqui ficam os wrappers que permitem usar libs externas com contatos do domínio.

Copyright BINGO Collaboration
Last modified: 2026-11-05
"""

from __future__ import annotations

from radioskysims_core.application.adapters.external_geometry import (
    SkyfieldGeometryProvider,
)

__all__ = ["SkyfieldGeometryProvider"]
