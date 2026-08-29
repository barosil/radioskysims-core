"""\
Módulo: packages/radioskysims-core/src/radioskysims_core/config/ports.py

Descrição:
    Port (contrato) de configuração — ``ConfigPort``. O núcleo do
    RadioSkySim consome esse contrato; implementações concretas (TOML,
    env, remoto) ficam em adapters.

Copyright BINGO Collaboration
Last modified: 2026-08-29
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any


class ConfigPort(ABC):
    """Contrato para carregamento de configurações."""

    @abstractmethod
    def load(
        self,
        key: str | None = None,
        *,
        settings_file: str | Path | None = None,
    ) -> dict[str, Any]:
        """Carrega a configuração (opcionalmente uma seção ``key``)."""
        raise NotImplementedError

    @abstractmethod
    def resolve_path(
        self,
        settings_file: str | Path | None = None,
    ) -> Path:
        """Resolve o caminho do arquivo de configuração a usar."""
        raise NotImplementedError

    @abstractmethod
    def set_active(self, filename: str | Path | None) -> Path | None:
        """Define o arquivo de configuração ativo (None = default)."""
        raise NotImplementedError
