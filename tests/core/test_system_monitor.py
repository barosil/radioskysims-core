"""Testes do SystemMonitor (radioskysims_core.monitor)."""

from __future__ import annotations

from radioskysims_core.monitor import SystemMonitor, check_resources


def test_system_monitor_snapshot() -> None:
    mon = SystemMonitor()
    res = mon.snapshot()
    assert res.cpu_count >= 1
    assert res.available_memory_mb > 0
    assert res.total_memory_mb >= res.available_memory_mb


def test_system_monitor_cpu_count() -> None:
    assert SystemMonitor().cpu_count >= 1


def test_estimated_footprint() -> None:
    mon = SystemMonitor()
    # 1000 x 256 x 1 x 2 x 1 elementos float64 com margem 3x
    mb = mon.estimated_footprint_mb(n_time=1000, n_freq=256, n_sources=1)
    assert mb > 0
    # footprint pequeno cabe em qualquer máquina razoável
    assert mon.can_fit(mb)


def test_ensure_resources_ok() -> None:
    # não deve levantar para um footprint minúsculo
    check_resources(footprint_mb=1.0)
