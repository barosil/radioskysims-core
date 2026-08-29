"""Testes do registro plugável de modelos SQLModel (radioskysims_core.db.models)."""

from __future__ import annotations

from radioskysims_core.db.models import (
    load_registered_models,
    register_model_module,
    registered_model_modules,
)


def test_register_and_list() -> None:
    register_model_module("radioskysims_core.db.models")
    assert "radioskysims_core.db.models" in registered_model_modules()


def test_register_is_idempotent() -> None:
    before = registered_model_modules()
    register_model_module("radioskysims_core.db.models")
    register_model_module("radioskysims_core.db.models")
    assert registered_model_modules() == before


def test_load_registered_models() -> None:
    # registra um módulo importável e carrega
    register_model_module("radioskysims_core.db.models")
    mods = load_registered_models()
    assert any(m.__name__ == "radioskysims_core.db.models" for m in mods)
