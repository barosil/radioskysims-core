"""\
Módulo: packages/radioskysims-core/src/radioskysims_core/db/job_repository.py

Descrição:
    Repositório de jobs sobre SQLite (MVP, ticket TOD-002). API mínima de
    criar/atualizar/consultar jobs usando SQLModel com ``sqlite://``
    (in-memory nos testes) ou um arquivo local.

Copyright BINGO Collaboration
Last modified: 2026-08-30
"""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

from sqlalchemy.engine import Engine
from sqlmodel import Session, SQLModel, create_engine, select

from radioskysims_core.db.jobs import Job, JobStatus

DEFAULT_JOBS_DB = "sqlite:///data/jobs.db"


def default_jobs_db() -> str:
    """URL SQLite padrão do banco de jobs, resolvida na RAÍZ do projeto.

    Ao contrário de ``DEFAULT_JOBS_DB`` (relativa ao CWD), usa a raiz detectada
    por ``get_project_root`` — caminho estável independente do diretório de
    execução (uniformização de caminhos — UX M4).
    """
    from radioskysims_core.paths import get_project_root

    db_path = get_project_root() / "data" / "jobs.db"
    return f"sqlite:///{db_path}"


def _status_value(status: JobStatus | str) -> str:
    """Normaliza um status (enum ou string) para o valor textual."""
    return status.value if isinstance(status, JobStatus) else str(status)


class JobRepository:
    """Persistência mínima de jobs em SQLite.

    Cria a tabela ``jobs`` no primeiro uso. Em testes, passe
    ``url="sqlite://"`` (in-memory) ou um arquivo temporário.
    """

    def __init__(self, url: str = DEFAULT_JOBS_DB) -> None:
        self.url = url
        self.engine: Engine = create_engine(url, future=True)
        SQLModel.metadata.create_all(self.engine)

    def create(
        self,
        *,
        name: str,
        config_path: str | Path | None = None,
    ) -> Job:
        """Cria um job no estado PENDING."""
        job = Job(name=name, config_path=str(config_path) if config_path else None)
        with Session(self.engine) as session:
            session.add(job)
            session.commit()
            session.refresh(job)
        return job

    def update_status(
        self,
        job_id: int,
        status: JobStatus | str,
        *,
        error: str | None = None,
        output_path: str | Path | None = None,
    ) -> Job | None:
        """Atualiza o status (e campos opcionais) de um job."""
        with Session(self.engine) as session:
            job = session.get(Job, job_id)
            if job is None:
                return None
            job.status = _status_value(status)
            if error is not None:
                job.error = error
            if output_path is not None:
                job.output_path = str(output_path)
            job.updated_at = datetime.now(UTC)
            session.add(job)
            session.commit()
            session.refresh(job)
        return job

    def update_progress(
        self,
        job_id: int,
        *,
        percent: float,
        step: str,
    ) -> Job | None:
        """Atualiza o progresso (0–100) e a etapa atual de um job."""
        with Session(self.engine) as session:
            job = session.get(Job, job_id)
            if job is None:
                return None
            job.progress_percent = max(0.0, min(100.0, float(percent)))
            job.progress_step = step
            job.updated_at = datetime.now(UTC)
            session.add(job)
            session.commit()
            session.refresh(job)
        return job

    def set_pid(self, job_id: int, pid: int | None) -> Job | None:
        """Associa o PID do worker ao job (execuções em background)."""
        with Session(self.engine) as session:
            job = session.get(Job, job_id)
            if job is None:
                return None
            job.pid = pid
            job.updated_at = datetime.now(UTC)
            session.add(job)
            session.commit()
            session.refresh(job)
        return job

    def get(self, job_id: int) -> Job | None:
        """Retorna um job por id (ou None)."""
        with Session(self.engine) as session:
            return session.get(Job, job_id)

    def list(
        self,
        *,
        status: JobStatus | str | None = None,
        limit: int = 100,
    ) -> list[Job]:
        """Lista jobs (opcionalmente filtrando por status), mais recentes primeiro."""
        stmt = select(Job).order_by(Job.created_at.desc()).limit(limit)
        if status is not None:
            stmt = (
                select(Job)
                .where(Job.status == _status_value(status))
                .order_by(Job.created_at.desc())
                .limit(limit)
            )
        with Session(self.engine) as session:
            return list(session.exec(stmt))

    def close(self) -> None:
        """Fecha a engine."""
        self.engine.dispose()


__all__ = ["DEFAULT_JOBS_DB", "JobRepository", "default_jobs_db"]
