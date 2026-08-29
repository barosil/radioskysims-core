"""
Módulo: packages/radioskysims-core/src/radioskysims_core/paths.py

Descrição:
    Gerenciamento de caminhos e diretórios do projeto RadioSkySim
    (generalizado no pacote core — PathManager).
    Define constantes para localização de dados, configurações e recursos,
    com suporte a execução em scripts e notebooks Jupyter. A raiz do projeto
    é detectada por marcadores (``pyproject.toml`` ou ``.git``), não pela
    localização física do módulo.

Copyright BINGO Collaboration
Last modified: 2026-08-29
"""

# paths.py
from __future__ import annotations

import tomllib  # Python 3.11+
from pathlib import Path

from dotenv import dotenv_values

# ============================================================
# Funções utilitárias
# ============================================================


def get_project_root() -> Path:
    """
    Retorna o diretório raiz do projeto RadioSkySim.

    Funciona tanto em scripts normais quanto em notebooks Jupyter.
    Procura por 'pyproject.toml' ou '.git' para detectar a raiz do projeto.

    Estratégia (independe da localização física do módulo):
      1. sobe a partir do CWD atual;
      2. se não achar, sobe a partir da localização deste arquivo.

    Returns:
        Path: Caminho absoluto para o diretório raiz do projeto.
    """
    candidates = [Path.cwd(), Path(__file__).resolve()]
    for start in candidates:
        for parent in [start, *start.parents]:
            if (parent / "pyproject.toml").exists() or (parent / ".git").exists():
                return parent
    return Path.cwd()


class PathManager:
    """Gerenciador de caminhos parametrizável pela raiz do projeto.

    Permite resolver todos os diretórios/arquivos do projeto a partir de
    uma raiz arbitrária (default: :func:`get_project_root`).
    """

    def __init__(self, root: str | Path | None = None) -> None:
        self.root = Path(root).resolve() if root is not None else get_project_root()

    # Diretórios principais
    @property
    def src_dir(self) -> Path:
        return self.root / "src/radioskysims"

    @property
    def data_dir(self) -> Path:
        return self.root / "data"

    @property
    def aux_dir(self) -> Path:
        return self.data_dir / "aux"

    @property
    def catalog_dir(self) -> Path:
        return self.data_dir / "raw/catalog"

    @property
    def satellite_dir(self) -> Path:
        return self.data_dir / "raw/satellites"

    @property
    def skymap_dir(self) -> Path:
        return self.data_dir / "raw/skymaps"

    @property
    def temp_dir(self) -> Path:
        return self.data_dir / "temp"

    @property
    def log_dir(self) -> Path:
        return self.data_dir / "logs"

    @property
    def notebooks_dir(self) -> Path:
        return self.root / "notebooks"

    # Arquivos específicos
    @property
    def settings_file(self) -> Path:
        return self.root / "settings.toml"

    @property
    def env_file(self) -> Path:
        return self.aux_dir / ".env"

    def load_config(self, path: Path | None = None) -> dict:
        """Lê o arquivo TOML de configuração (default: settings.toml)."""
        p = path or self.settings_file
        if not p.exists():
            msg = f"Config file not found: {p}"
            raise FileNotFoundError(msg)
        return tomllib.loads(p.read_text(encoding="utf-8"))

    def load_env(self, path: Path | None = None) -> dict:
        """Carrega variáveis de ambiente a partir de um arquivo .env."""
        p = path or self.env_file
        if p.exists():
            return dotenv_values(dotenv_path=p)
        return {}


# ============================================================
# Diretórios principais (compatibilidade com o monólito)
# ============================================================

ROOT = get_project_root()
SRC_DIR = ROOT / "src/radioskysims"

# Pastas de dados
DATA_DIR = ROOT / "data"
AUX_DIR = DATA_DIR / "aux"
CATALOG_DIR = DATA_DIR / "raw/catalog"
SATELLITE_DIR = DATA_DIR / "raw/satellites"
SKYMAP_DIR = DATA_DIR / "raw/skymaps"
TEMP_DIR = DATA_DIR / "temp"
LOG_DIR = DATA_DIR / "logs"

NOTEBOOKS_DIR = ROOT / "notebooks"

# ============================================================
# Arquivos específicos
# ============================================================

# Arquivo principal de configurações do projeto
SETTINGS_FILE = ROOT / "settings.toml"

# Arquivo .env auxiliar (para notebooks/scripts locais)
ENV_FILE = AUX_DIR / ".env"

# ============================================================
# Funções de carregamento (compatibilidade)
# ============================================================


def load_config(path: Path = SETTINGS_FILE) -> dict:
    """
    Lê o arquivo TOML de configuração.
    Retorna um dicionário Python.
    """
    if not path.exists():
        msg = f"Config file not found: {path}"
        raise FileNotFoundError(msg)
    return tomllib.loads(path.read_text(encoding="utf-8"))


def load_env(path: Path = ENV_FILE) -> dict:
    """
    Carrega variáveis de ambiente a partir de um arquivo .env.
    """
    if path.exists():
        return dotenv_values(dotenv_path=path)
    return {}
