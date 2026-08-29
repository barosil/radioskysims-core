"""Testes do contrato de configuração (ConfigPort / TomlConfigAdapter)."""

from __future__ import annotations

import pytest
from radioskysims_core.config import ConfigPort, TomlConfigAdapter


def test_config_port_is_abstract() -> None:
    with pytest.raises(TypeError):
        ConfigPort()  # type: ignore[abstract]


def test_toml_config_adapter_loads_section() -> None:
    adapter = TomlConfigAdapter()
    cfg = adapter.load("radiosources")
    assert isinstance(cfg, dict)


def test_toml_config_adapter_resolve_path() -> None:
    adapter = TomlConfigAdapter()
    path = adapter.resolve_path()
    assert path.name == "settings.toml"
    assert path.exists()


def test_toml_config_adapter_set_active() -> None:
    adapter = TomlConfigAdapter()
    try:
        adapter.set_active(None)
        path = adapter.resolve_path()
        assert path.name == "settings.toml"
    finally:
        adapter.set_active(None)
