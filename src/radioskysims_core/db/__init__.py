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

# Nota: a engine async (aengine) NÃO é importada aqui — é 100% lazy e só é
# criada sob demanda (evita efeito colateral/ruído no import; asyncpg é
# opcional, via extra de banco). Não existe classe `AsyncDatabase` concreta
# neste pacote.

__all__ = [
    "Database",
    "Job",
    "JobRepository",
    "JobStatus",
    "load_registered_models",
    "register_model_module",
]
