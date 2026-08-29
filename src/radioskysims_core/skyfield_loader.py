"""
Módulo: src/radioskysims/infrastructure/external/skyfield_loader.py

Descrição:
    Utilitário para carregamento e cache de efemérides Skyfield.
    Armazena os arquivos .bsp em data/aux/skyfield/ conforme
    configurado em settings.toml ([paths] skyfield_folder).

Copyright BINGO Collaboration
Last modified: 2026-07-27
"""

from __future__ import annotations

import logging
from pathlib import Path

from skyfield.api import Loader

from radioskysims_core.config.config_loader import load_config
from radioskysims_core.paths import ROOT

logger = logging.getLogger(__name__)

# Nome padrão da efeméride
DEFAULT_EPHEMERIS = "de421.bsp"


def get_skyfield_dir() -> Path:
    """Retorna o diretório de cache das efemérides Skyfield.

    Lê de ``settings.toml [paths] skyfield_folder`` ou usa o
    fallback ``data/aux/skyfield/``.
    """
    cfg = load_config("paths") or {}
    folder = cfg.get("skyfield_folder", "data/aux/skyfield/")
    sky_dir = Path(folder).expanduser()
    # Caminho relativo é ancorado na raiz do projeto (notebooks têm CWD próprio)
    if not sky_dir.is_absolute():
        sky_dir = ROOT / sky_dir
    sky_dir = sky_dir.resolve()
    sky_dir.mkdir(parents=True, exist_ok=True)
    return sky_dir


def load_ephemeris(name: str = DEFAULT_EPHEMERIS):
    """Carrega (e baixa se necessário) uma efeméride Skyfield.

    O arquivo é armazenado em ``get_skyfield_dir() / name``,
    evitando poluir a raiz do projeto.

    Args:
        name: Nome do arquivo .bsp (ex: ``"de421.bsp"``).

    Returns:
        Objeto efeméride carregado pelo Skyfield.
    """
    sky_dir = get_skyfield_dir()
    bsp_path = sky_dir / name
    logger.info("Carregando efeméride Skyfield: %s", bsp_path)
    loader = Loader(sky_dir)
    return loader(name)
