"""Testes do modelo Job e JobRepository (radioskysims_core.db.jobs / job_repository)."""

from __future__ import annotations

import pytest
from radioskysims_core.db.job_repository import JobRepository
from radioskysims_core.db.jobs import JobStatus


@pytest.fixture
def repo() -> JobRepository:
    """Repositório sobre SQLite in-memory (isolado por teste)."""
    r = JobRepository(url="sqlite://")
    yield r
    r.close()


def test_create_job(repo: JobRepository) -> None:
    job = repo.create(name="tod-run")
    assert job.id is not None
    assert job.status == JobStatus.PENDING.value
    assert job.progress_percent == 0.0


def test_lifecycle_create_update_read(repo: JobRepository) -> None:
    job = repo.create(name="tod-run", config_path="settings.toml")
    assert job.id is not None

    repo.update_status(job.id, JobStatus.RUNNING)
    repo.update_progress(job.id, percent=50.0, step="tracks")
    repo.update_status(job.id, JobStatus.SUCCESS, output_path="data/TOD/out.nc")

    loaded = repo.get(job.id)
    assert loaded is not None
    assert loaded.status == JobStatus.SUCCESS.value
    assert loaded.progress_percent == 50.0
    assert loaded.progress_step == "tracks"
    assert loaded.output_path == "data/TOD/out.nc"
    assert loaded.config_path == "settings.toml"


def test_update_status_string(repo: JobRepository) -> None:
    job = repo.create(name="a")
    assert job.id is not None
    repo.update_status(job.id, "RUNNING")
    assert repo.get(job.id) is not None
    assert repo.get(job.id).status == JobStatus.RUNNING.value


def test_update_status_missing_job_returns_none(repo: JobRepository) -> None:
    assert repo.update_status(999, JobStatus.FAILED) is None


def test_update_progress_clamps(repo: JobRepository) -> None:
    job = repo.create(name="c")
    assert job.id is not None
    repo.update_progress(job.id, percent=150.0, step="x")
    assert repo.get(job.id).progress_percent == 100.0


def test_list_filters_by_status(repo: JobRepository) -> None:
    a = repo.create(name="a")
    b = repo.create(name="b")
    assert a.id is not None
    assert b.id is not None
    repo.update_status(b.id, JobStatus.RUNNING)

    pending = repo.list(status=JobStatus.PENDING)
    running = repo.list(status="RUNNING")
    all_jobs = repo.list()

    assert len(pending) == 1
    assert pending[0].name == "a"
    assert len(running) == 1
    assert running[0].name == "b"
    assert len(all_jobs) == 2


def test_failed_job_records_error(repo: JobRepository) -> None:
    job = repo.create(name="f")
    assert job.id is not None
    repo.update_status(job.id, JobStatus.FAILED, error="boom")
    loaded = repo.get(job.id)
    assert loaded is not None
    assert loaded.status == JobStatus.FAILED.value
    assert loaded.error == "boom"
