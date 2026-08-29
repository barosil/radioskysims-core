"""\
Módulo: packages/radioskysims-core/src/radioskysims_core/config/adapters.py

Descrição:
    Implementação concreta do ``ConfigPort`` via TOML — ``TomlConfigAdapter``.
    Encapsula a API legada de ``radioskysims_core.config.config_loader``
    (load_config / resolve_settings_path / set_settings_file) sob o contrato
    ``ConfigPort``, permitindo troca de fonte de configuração sem mudar
    os consumidores.

Copyright BINGO Collaboration
Last modified: 2026-08-29
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from .config_loader import load_config, resolve_settings_path, set_settings_file
from .ports import ConfigPort


class TomlConfigAdapter(ConfigPort):
    """Adapter de configuração baseado em arquivos TOML (implementação atual)."""

    def load(
        self,
        key: str | None = None,
        *,
        settings_file: str | Path | None = None,
    ) -> dict[str, Any]:
        return load_config(key, settings_file=settings_file)

    def resolve_path(
        self,
        settings_file: str | Path | None = None,
    ) -> Path:
        return resolve_settings_path(settings_file)

    def set_active(self, filename: str | Path | None) -> Path | None:
        return set_settings_file(filename)
