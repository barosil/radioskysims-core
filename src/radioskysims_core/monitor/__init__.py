"""\
Pacote: radioskysims_core.monitor

Monitoramento de recursos da máquina (CPU, memória, disco) de forma
genérica e standalone — usável por qualquer aplicação antes de operações
pesadas.

Copyright BINGO Collaboration
Last modified: 2026-08-29
"""

from __future__ import annotations

from .system_monitor import SystemMonitor, check_resources

__all__ = ["SystemMonitor", "check_resources"]
