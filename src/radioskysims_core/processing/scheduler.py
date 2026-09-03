"""\
Módulo: radioskysims_core/processing/scheduler.py

Implementação concreta (infraestrutura do core) de seleção/gerência do
scheduler dask — UX Onda 3/R6 (decisão: processamento no core; implícito
local vs explícito distributed/mpi/gpu).

Semântica equivalente à usada pelo ``ResourceAwareProcessor`` de
``radioskysims-simulation`` (que passará a consumir este módulo na F2/E5).

Copyright BINGO Collaboration
Last modified: 2026-09-03
"""

from __future__ import annotations

import logging
from typing import Any

log = logging.getLogger(__name__)


class DaskScheduler:
    """Configura/gerencia o scheduler dask (threads/synchronous/distributed).

    - ``"synchronous"``: single-thread.
    - ``"threads"`` (padrão): threads com ``num_workers = cpu_count``.
    - ``"distributed"``: sobe ``LocalCluster`` + ``Client`` (dashboard);
      se ``distributed`` não estiver instalado, cai para ``threads``.
    """

    def __init__(
        self,
        *,
        scheduler: str = "threads",
        processes: bool | None = None,
        num_workers: int | None = None,
        logger: Any | None = None,
    ) -> None:
        self._scheduler = scheduler
        self._processes = processes
        self._num_workers = num_workers
        self._log = logger or log
        self._cluster: Any | None = None
        self._client: Any | None = None
        self._dashboard_url: str | None = None

    # ── API ────────────────────────────────────────────────────
    def configure(self, *, cpu_count: int) -> str:
        """Aplica a configuração do scheduler dask.

        Returns:
            Scheduler efetivo usado (``synchronous``/``threads``/``distributed``).
        """
        if self._scheduler == "distributed":
            if self.start_distributed(cpu_count=cpu_count):
                return "distributed"
            self._log.warning("distributed_unavailable: fallback para threads")
            self._scheduler = "threads"

        import dask

        if cpu_count <= 1 or self._scheduler == "synchronous":
            dask.config.set(scheduler="synchronous")
            self._log.info("dask_scheduler", extra={"scheduler": "synchronous"})
            return "synchronous"

        from dask.config import set as dask_set

        n_workers = self._num_workers or cpu_count
        dask_set({"num_workers": n_workers})
        dask.config.set(scheduler="threads")
        self._log.info(
            "dask_scheduler",
            extra={"scheduler": "threads", "num_workers": n_workers},
        )
        return "threads"

    def start_distributed(self, *, cpu_count: int) -> bool:
        """Sobe LocalCluster + Client com dashboard (processos ou threads).

        Returns:
            ``True`` se iniciou; ``False`` se ``distributed`` ausente/falhou.
        """
        try:
            from distributed import Client, LocalCluster
        except ImportError:
            return False

        processes = self._processes
        if processes is None:
            processes = True  # padrão: workers em processos separados

        try:
            if processes:
                cluster = LocalCluster(
                    n_workers=max(1, self._num_workers or cpu_count),
                    threads_per_worker=1,
                    processes=True,
                    dashboard_address=":0",
                )
            else:
                cluster = LocalCluster(
                    n_workers=1,
                    threads_per_worker=max(1, self._num_workers or cpu_count),
                    processes=False,
                    dashboard_address=":0",
                )
            client = Client(cluster)
        except Exception as exc:
            self._log.warning("distributed_start_failed", extra={"error": str(exc)})
            return False

        self._cluster = cluster
        self._client = client
        self._dashboard_url = client.dashboard_link
        self._log.info(
            "dask_dashboard",
            extra={
                "scheduler": "distributed",
                "dashboard_url": self._dashboard_url,
            },
        )
        return True

    @property
    def dashboard_url(self) -> str | None:
        """URL do dashboard (somente com scheduler ``distributed``)."""
        return self._dashboard_url

    @property
    def client(self) -> Any | None:
        return self._client

    def close(self) -> None:
        """Fecha client/cluster distribuído, se alocado."""
        if self._client is not None:
            try:
                self._client.close()
            except Exception:  # noqa: BLE001 - fechamento best-effort
                pass
            self._client = None
        if self._cluster is not None:
            try:
                self._cluster.close()
            except Exception:  # noqa: BLE001 - fechamento best-effort
                pass
            self._cluster = None
        self._dashboard_url = None

    def __enter__(self) -> "DaskScheduler":
        return self

    def __exit__(self, *exc: Any) -> bool:
        self.close()
        return False


__all__ = ["DaskScheduler"]
