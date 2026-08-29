"""\
Módulo: packages/radioskysims-core/src/radioskysims_core/progress.py

Descrição:
    Indicador de progresso uniforme para operações longas do ecossistema
    RadioSkySim (downloads, ingestão, escrita em DB, operações CPU-bound).
    Requisito "Messages" do plano de desacoplamento (`.prompts/decoupling.md`).

    Usa ``tqdm`` quando disponível e cai para um logger simples caso contrário.

Copyright BINGO Collaboration
Last modified: 2026-08-29
"""

from __future__ import annotations

import logging
from collections.abc import Iterable, Iterator
from typing import Any, TypeVar

log = logging.getLogger(__name__)

try:  # tqdm é uma dependência leve e comum; fallback sem ela
    from tqdm.auto import tqdm as _tqdm
except Exception:  # pragma: no cover
    _tqdm = None

T = TypeVar("T")


def progress_bar(
    iterable: Iterable[T] | None = None,
    *,
    total: int | None = None,
    desc: str = "",
    unit: str = "it",
    **kwargs: Any,
) -> Any:
    """Cria uma barra de progresso uniforme.

    Retorna um iterável/contexto de progresso. Quando ``tqdm`` não está
    disponível, loga o progresso em passos de 10%.

    Exemplo::

        for item in progress_bar(items, total=len(items), desc="Ingestão"):
            process(item)
    """
    if _tqdm is not None:
        return _tqdm(iterable, total=total, desc=desc, unit=unit, **kwargs)
    return _FallbackProgress(iterable, total=total, desc=desc, unit=unit)


class _FallbackProgress(Iterator[T]):
    """Fallback simples sem tqdm: loga a cada 10%."""

    def __init__(
        self,
        iterable: Iterable[T] | None,
        *,
        total: int | None = None,
        desc: str = "",
        unit: str = "it",
    ) -> None:
        self._it = iter(iterable) if iterable is not None else iter(())
        self._total = total
        self._desc = desc
        self._unit = unit
        self._count = 0
        self._last_pct = -1

    def __iter__(self) -> "_FallbackProgress[T]":
        return self

    def __next__(self) -> T:
        try:
            item = next(self._it)
        except StopIteration:
            log.info("%s: concluído (%d %s)", self._desc or "Progresso", self._count, self._unit)
            raise
        self._count += 1
        if self._total:
            pct = int(100 * self._count / self._total)
            if pct % 10 == 0 and pct != self._last_pct:
                self._last_pct = pct
                log.info(
                    "%s: %d%% (%d/%d %s)",
                    self._desc or "Progresso",
                    pct,
                    self._count,
                    self._total,
                    self._unit,
                )
        return item

    def update(self, n: int = 1) -> None:  # compat com tqdm
        self._count += n

    def close(self) -> None:  # compat com tqdm
        pass


def log_operation_start(operation: str, **details: Any) -> None:
    """Informa o início de uma operação longa (requisito Messages)."""
    if details:
        log.info("[start] %s: %s", operation, details)
    else:
        log.info("[start] %s", operation)


def log_operation_end(operation: str, *, status: str = "ok", **details: Any) -> None:
    """Informa o fim de uma operação longa (requisito Messages)."""
    if details:
        log.info("[end] %s (status=%s): %s", operation, status, details)
    else:
        log.info("[end] %s (status=%s)", operation, status)


__all__ = [
    "log_operation_end",
    "log_operation_start",
    "progress_bar",
]
