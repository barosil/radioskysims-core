"""\
Pacote: radioskysims_core.processing

Implementações concretas de processamento (infraestrutura do core) —
UX Onda 3/R6. Contrato em ``radioskysims_core.application.ports.processing``.

    DaskScheduler  (threads / synchronous / distributed)

Copyright BINGO Collaboration
"""

from radioskysims_core.processing.scheduler import DaskScheduler

__all__ = ["DaskScheduler"]
