"""\
Pacote: radioskysims_core.db

Base de infraestrutura de banco de dados do ecossistema RadioSkySim:
- engine: Database (síncrono) e AsyncDatabase (assíncrono)
- models: registro de modelos SQLModel plugável (cada pacote de domínio
  registra suas próprias tabelas)

Copyright BINGO Collaboration
Last modified: 2026-08-29
"""

from __future__ import annotations

from .engine import Database
from .job_repository import JobRepository
from .jobs import Job, JobStatus
from .models import load_registered_models, register_model_module

try:  # aengine depende de drivers async (asyncpg); opcional
    from .aengine import AsyncDatabase  # noqa: F401
except Exception:  # pragma: no cover
    AsyncDatabase = None  # type: ignore[assignment,misc]

__all__ = [
    "AsyncDatabase",
    "Database",
    "Job",
    "JobRepository",
    "JobStatus",
    "load_registered_models",
    "register_model_module",
]
