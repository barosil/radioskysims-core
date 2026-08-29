"""\
Módulo: packages/radioskysims-core/src/radioskysims_core/db/models.py

Descrição:
    Base dos modelos SQLModel compartilhados do ecossistema RadioSkySim,
    com **registro de schema plugável**: cada pacote de domínio registra
    suas próprias tabelas via :func:`register_model_module`, e
    :func:`load_registered_models` as importa (registrando-as em
    ``SQLModel.metadata``) antes de ``create_all``.

    O monólito legado agrega essas tabelas em
    ``radioskysims.infrastructure.db.models`` (mantido via shim).

Copyright BINGO Collaboration
Last modified: 2026-08-29
"""

from __future__ import annotations

import importlib
from types import ModuleType

# Módulos de modelos SQLModel registrados pelos pacotes de domínio
# (ex.: "radioskysims_beam.infrastructure.db.models").
_MODEL_MODULES: list[str] = []


def register_model_module(module_name: str) -> None:
    """Registra um módulo de modelos SQLModel (schema plugável).

    Args:
        module_name: nome totalmente qualificado do módulo que define
            tabelas SQLModel (ex.: ``"radioskysims_beam.infrastructure.db.models"``).
    """
    if module_name not in _MODEL_MODULES:
        _MODEL_MODULES.append(module_name)


def load_registered_models() -> list[ModuleType]:
    """Importa (e registra no ``SQLModel.metadata``) os módulos registrados.

    Retorna os módulos importados. Deve ser chamado antes de
    ``SQLModel.metadata.create_all(engine)``.
    """
    return [importlib.import_module(name) for name in _MODEL_MODULES]


def registered_model_modules() -> tuple[str, ...]:
    """Lista os nomes dos módulos de modelos registrados."""
    return tuple(_MODEL_MODULES)


__all__ = [
    "load_registered_models",
    "register_model_module",
    "registered_model_modules",
]
