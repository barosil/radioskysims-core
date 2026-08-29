"""
Módulo: src/radioskysims/infrastructure/config/settings.py

Descrição:
    Gerenciamento de configurações da aplicação usando Pydantic Settings.
    Carrega configurações de arquivos TOML e variáveis de ambiente,
    fornecendo uma interface tipada e validada.
"""

from __future__ import annotations

from pathlib import Path

import tomllib
from pydantic import BaseModel
from pydantic_settings import BaseSettings, SettingsConfigDict

from radioskysims_core.paths import get_project_root

# Arquivo padrão de configurações passa a ser o settings.toml na raiz do projeto
toml_path = get_project_root() / "settings.toml"


class Paths(BaseModel):
    """
    Configurações de caminhos do projeto.

    Attributes:
        sat_signals (Path | None): Caminho para arquivos de sinais de satélites.
    """

    sat_signals: Path | None = None


class Settings(BaseSettings):
    """
    Configurações globais da aplicação RadioSkySim.

    Carrega configurações de arquivos TOML e variáveis de ambiente (.env),
    com suporte a validação de tipos via Pydantic.

    Attributes:
        paths (Paths): Configurações de caminhos.
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_nested_delimiter="__",
    )

    paths: Paths = Paths()

    @classmethod
    def load(cls, toml_path: str | Path | None = None) -> Settings:
        """
        Carrega configurações de arquivo TOML e mescla com variáveis de ambiente.

        Args:
            toml_path (str | Path | None): Caminho customizado para settings.toml.
                Se None, usa settings.toml no mesmo diretório deste módulo.

        Returns:
            Settings: Instância configurada com valores do TOML e .env.

        Notes:
            Variáveis de ambiente (.env) têm precedência sobre o TOML.
        """
        if toml_path is None:
            # resolve settings.toml na raiz do projeto
            toml_path = get_project_root() / "settings.toml"

        data = {}
        if Path(toml_path).exists():
            with Path(toml_path).open("rb") as f:
                data = tomllib.load(f)

        return cls(**data)


# instância única
settings = Settings.load()
