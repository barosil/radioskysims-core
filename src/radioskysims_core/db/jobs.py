"""\
Módulo: packages/radioskysims-core/src/radioskysims_core/db/jobs.py

Descrição:
    Modelo SQLModel ``Job`` (tabela ``jobs``) para rastreamento de execuções
    (foreground/background) — ticket TOD-002. Registra-se no schema plugável
    (``register_model_module``) para ser criado pelo ``init_db`` do umbrella.

Copyright BINGO Collaboration
Last modified: 2026-08-30
"""

from __future__ import annotations

from datetime import UTC, datetime
from enum import Enum

from sqlmodel import Field, SQLModel

from radioskysims_core.db.models import register_model_module


class JobStatus(str, Enum):
    """Estados do ciclo de vida de um job."""

    PENDING = "PENDING"
    RUNNING = "RUNNING"
    SUCCESS = "SUCCESS"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"


class Job(SQLModel, table=True):  # type: ignore[call-arg, misc]
    """Registro persistente de uma execução (job) de simulação."""

    __tablename__ = "jobs"

    id: int | None = Field(default=None, primary_key=True)
    name: str = Field(index=True)
    status: str = Field(default=JobStatus.PENDING.value, index=True)
    pid: int | None = Field(default=None, description="PID do worker (background).")
    config_path: str | None = Field(default=None, description="Settings usados na execução.")
    output_path: str | None = Field(default=None, description="Dataset gerado (HDF5/Zarr).")
    error: str | None = Field(default=None, description="Mensagem de erro, se falhou.")
    progress_percent: float = Field(default=0.0, ge=0.0, le=100.0)
    progress_step: str = Field(default="", description="Etapa atual (ex.: 'tracks').")
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


register_model_module(__name__)


__all__ = ["Job", "JobStatus"]
