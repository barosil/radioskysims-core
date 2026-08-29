"""Testes do indicador de progresso (radioskysims_core.progress)."""

from __future__ import annotations

from radioskysims_core.progress import log_operation_end, log_operation_start, progress_bar


def test_progress_bar_iterates() -> None:
    items = list(range(10))
    seen = list(progress_bar(items, total=len(items), desc="teste"))
    assert seen == items


def test_progress_bar_empty() -> None:
    assert list(progress_bar([], total=0)) == []


def test_log_operation_messages() -> None:
    # apenas verifica que não levantam (logam via logging)
    log_operation_start("download", url="http://example")
    log_operation_end("download", status="ok", bytes=1024)
