"""\
Módulo: tests/core/test_processing_scheduler.py

Descrição:
    Testes do ``DaskScheduler`` do core (UX Onda 3/R6) — threads/synchronous.

Copyright BINGO Collaboration
"""

from __future__ import annotations

import dask.array as da
from radioskysims_core.application.ports.processing import (
    ProcessingConfig,
    ProcessorPort,
)
from radioskysims_core.processing import DaskScheduler


def test_configure_threads_e_executa():
    sched = DaskScheduler(scheduler="threads")
    try:
        effective = sched.configure(cpu_count=2)
        assert effective == "threads"
        result = (da.ones((4, 4)) * 2).sum().compute()
        assert result == 32
    finally:
        sched.close()


def test_configure_synchronous_com_1_cpu():
    sched = DaskScheduler(scheduler="synchronous")
    try:
        effective = sched.configure(cpu_count=1)
        assert effective == "synchronous"
        assert (da.ones(3).sum().compute()) == 3
    finally:
        sched.close()


def test_contrato_processorport_importavel():
    cfg = ProcessingConfig(scheduler="threads")
    assert cfg.scheduler == "threads"
    assert ProcessorPort.__name__ == "ProcessorPort"
