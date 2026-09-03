"""\
Módulo: radioskysims_core/application/ports/processing.py

Contrato de processamento ciente de recursos (UX — Onda 3/R6).

Decisão registrada: a abstração de processamento (domínio/ports + configuração)
vive no ``radioskysims_core``; as implementações concretas (schedulers dask,
local/distributed/mpi/gpu) ficam em ``radioskysims_core.processing``
(infraestrutura do core). O ``ResourceAwareProcessor`` de
``radioskysims-simulation`` será migrado para consumir este contrato de forma
incremental (F2/E5).

Copyright BINGO Collaboration
Last modified: 2026-09-03
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any, Generic, TypeVar

_W = TypeVar("_W")  # workload
_R = TypeVar("_R")  # resultado


@dataclass(frozen=True)
class ProcessingConfig:
    """Configuração de execução de um processor.

    Attributes:
        scheduler: Scheduler dask — ``"threads"`` (padrão), ``"synchronous"``
            ou ``"distributed"`` (LocalCluster + dashboard).
        processes: ``True`` → workers em processos; ``False`` → 1 worker com
            threads; ``None`` → padrão (processos).
        num_workers: Nº de workers/threads (default: detectado por CPU).
        max_batch_mb: Limite de memória por batch (opcional).
    """

    scheduler: str = "threads"
    processes: bool | None = None
    num_workers: int | None = None
    max_batch_mb: float | None = None


class ProcessorPort(ABC, Generic[_W, _R]):
    """Processor ciente de recursos (implícito vs explícito).

    - **Implícito (padrão)**: scheduler dask local (threads/synchronous),
      sem o usuário gerenciar cluster.
    - **Explícito**: ``distributed`` (LocalCluster), ``mpi``/``gpu`` (futuro)
      para desenvolvimento/escala.
    """

    @abstractmethod
    def process(self, workload: _W, *, config: ProcessingConfig | None = None) -> _R:
        """Executa o workload em batches seguros para memória."""

    @abstractmethod
    def shutdown(self) -> None:
        """Encerra recursos alocados (cluster/client, se houver)."""

    def __enter__(self) -> "ProcessorPort[_W, _R]":
        return self

    def __exit__(self, *exc: Any) -> bool:
        self.shutdown()
        return False


__all__ = ["ProcessingConfig", "ProcessorPort"]
