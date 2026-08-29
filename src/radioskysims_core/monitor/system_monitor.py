"""\
Módulo: packages/radioskysims-core/src/radioskysims_core/monitor/system_monitor.py

Descrição:
    Detecção de recursos da máquina (CPU, memória, disco) de forma genérica,
    extraída do ResourceAwareProcessor do monólito (radioskysims.infrastructure.
    processing.resource_processor). Standalone e sem dependência de domínio —
    usável por qualquer aplicação para decidir com segurança antes de operações
    pesadas (evitando travamentos por falta de memória/disco).

Copyright BINGO Collaboration
Last modified: 2026-08-29
"""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass
from typing import Any

log = logging.getLogger(__name__)

# Margem de segurança multiplicativa sobre a estimativa teórica de memória
_SAFETY_FACTOR = 3.0
# Memória reservada para o sistema/sobrecarga Python (MB)
_SYSTEM_RESERVE_MB = 512.0


@dataclass(frozen=True)
class SystemResources:
    """Snapshot de recursos disponíveis na máquina."""

    cpu_count: int
    available_memory_mb: float
    total_memory_mb: float
    available_disk_mb: float | None = None

    @property
    def usable_cpu_count(self) -> int:
        """Nº de CPUs que podem ser usados (>=1)."""
        return max(1, self.cpu_count)

    def as_dict(self) -> dict[str, Any]:
        """Representação serializável (logging/métricas)."""
        return {
            "cpu_count": self.cpu_count,
            "available_memory_mb": round(self.available_memory_mb, 1),
            "total_memory_mb": round(self.total_memory_mb, 1),
            "available_disk_mb": (
                round(self.available_disk_mb, 1) if self.available_disk_mb is not None else None
            ),
        }


def _detect_memory_mb() -> tuple[float, float]:
    """Retorna (memória disponível MB, memória total MB).

    Usa ``psutil`` quando disponível; caso contrário, assume um valor
    conservador (fallback 4096 MB disponíveis) e loga um aviso.
    """
    try:
        import psutil

        mem = psutil.virtual_memory()
        return float(mem.available) / (1024 * 1024), float(mem.total) / (1024 * 1024)
    except Exception:
        log.warning(
            "psutil não disponível. Assumindo %.0f MB de memória disponível. "
            "Instale psutil para detecção automática.",
            4096.0,
        )
        return 4096.0, 4096.0


def _detect_disk_mb(path: str | os.PathLike[str] = ".") -> float | None:
    """Espaço livre em disco (MB) no filesystem de ``path`` (psutil)."""
    try:
        import psutil

        usage = psutil.disk_usage(str(path))
        return float(usage.free) / (1024 * 1024)
    except Exception:
        return None


class SystemMonitor:
    """Monitora recursos da máquina (CPU/memória/disco).

    Exemplo::

        mon = SystemMonitor()
        res = mon.snapshot()
        if res.available_memory_mb < 2048:
            raise MemoryError("Memória insuficiente para a operação.")
    """

    def snapshot(self, *, disk_path: str | os.PathLike[str] | None = None) -> SystemResources:
        """Captura o estado atual dos recursos."""
        n_cpus = os.cpu_count() or 4
        avail_mb, total_mb = _detect_memory_mb()
        disk_mb = _detect_disk_mb(disk_path) if disk_path is not None else None
        return SystemResources(
            cpu_count=n_cpus,
            available_memory_mb=avail_mb,
            total_memory_mb=total_mb,
            available_disk_mb=disk_mb,
        )

    @property
    def cpu_count(self) -> int:
        """Nº de CPUs lógicos disponíveis."""
        return self.snapshot().cpu_count

    @property
    def available_memory_mb(self) -> float:
        """Memória disponível (MB)."""
        return self.snapshot().available_memory_mb

    def estimated_footprint_mb(self, bytes_per_element: int = 8, **shape: int) -> float:
        """Estima o footprint de um tensor com a forma dada (MB).

        Args:
            bytes_per_element: bytes por elemento (8 para float64).
            **shape: dimensões do tensor (ex.: n_time=1000, n_freq=256).

        Returns:
            Footprint estimado em MB, já com a margem de segurança.
        """
        n_elements = 1
        for dim in shape.values():
            n_elements *= max(1, int(dim))
        raw_mb = float(n_elements * bytes_per_element) / (1024 * 1024)
        return raw_mb * _SAFETY_FACTOR

    def can_fit(self, footprint_mb: float, *, reserved_mb: float = _SYSTEM_RESERVE_MB) -> bool:
        """True se ``footprint_mb`` cabe na memória disponível (com reserva)."""
        return footprint_mb + reserved_mb <= self.available_memory_mb

    def ensure_resources(
        self,
        footprint_mb: float,
        *,
        reserved_mb: float = _SYSTEM_RESERVE_MB,
        min_disk_mb: float | None = None,
        disk_path: str | os.PathLike[str] = ".",
    ) -> None:
        """Levanta exceção se os recursos forem insuficientes para ``footprint_mb``.

        Args:
            footprint_mb: footprint estimado da operação (MB).
            reserved_mb: reserva de segurança para o sistema (MB).
            min_disk_mb: espaço mínimo em disco exigido (MB) — opcional.
            disk_path: caminho usado para checar o disco.

        Raises:
            MemoryError: se não houver memória suficiente.
            OSError: se não houver espaço em disco suficiente.
        """
        res = self.snapshot(disk_path=disk_path)
        if not self.can_fit(footprint_mb, reserved_mb=reserved_mb):
            raise MemoryError(
                f"Memória insuficiente: footprint ~{footprint_mb:.0f} MB + reserva "
                f"{reserved_mb:.0f} MB > disponível {res.available_memory_mb:.0f} MB"
            )
        if min_disk_mb is not None and res.available_disk_mb is not None:
            if res.available_disk_mb < min_disk_mb:
                raise OSError(
                    f"Espaço em disco insuficiente: {res.available_disk_mb:.0f} MB "
                    f"disponíveis < {min_disk_mb:.0f} MB exigidos"
                )
        log.debug("Recursos OK: %s", res.as_dict())


def check_resources(*, footprint_mb: float, **kwargs: Any) -> None:
    """Atalho funcional para ``SystemMonitor().ensure_resources(...)``."""
    SystemMonitor().ensure_resources(footprint_mb, **kwargs)
