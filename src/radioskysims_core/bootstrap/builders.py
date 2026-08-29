"""Builders de componentes do pacote (composition root — strategy).
Extraído de ``radioskysims.bootstrap.builders`` na Fase 5.
Copyright BINGO Collaboration
"""

from __future__ import annotations

from typing import Any

from radioskysims_core.db.engine import Database
from radioskysims_core.logging_config import get_logger


def build_logging() -> dict[str, Any]:
    """Constroi loggers de aplicacao usados no wiring oficial."""

    return {
        "satellite_logger": get_logger("radioskysims.satellite_service"),
        "simulation_logger": get_logger("radioskysims.simulation"),
        "orchestrator_logger": get_logger("radioskysims.sim_orchestrator"),
    }


def build_database() -> Database:
    """Constroi dependencia concreta de banco de dados."""

    return Database()
