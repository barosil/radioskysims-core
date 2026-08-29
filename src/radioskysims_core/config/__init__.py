"""\
Pacote: radioskysims_core.config

Contratos e implementação de carregamento de configurações:
- ports.ConfigPort (ABC)
- adapters.TomlConfigAdapter (implementação atual via TOML)
- config_loader: API legada (load_config, resolve_settings_path, ...)

Copyright BINGO Collaboration
Last modified: 2026-08-29
"""

from __future__ import annotations

from .adapters import TomlConfigAdapter
from .ports import ConfigPort

__all__ = ["ConfigPort", "TomlConfigAdapter"]
