"""
Módulo: src/radioskysims/domain/common/logging.py

Logger estruturado de domínio — abstração leve para logging no domínio.

Permite logging estruturado (event + kwargs) sem depender de
infraestrutura externa como `infrastructure.logging_config`.
A configuração real (formato, destino) é feita na camada de
aplicação/infraestrutura.

Copyright BINGO Collaboration
Last modified: 2026-07-26
"""

from __future__ import annotations

import logging
from typing import Any


class DomainLogger:
    """Logger estruturado para uso nos módulos de domínio.

    Aceita um evento nomeado como primeiro argumento e kwargs
    como campos estruturados, sem depender de infraestrutura externa.
    """

    def __init__(self, name: str) -> None:
        self._logger = logging.getLogger(name)

    def debug(self, event: str, **kwargs: Any) -> None:
        exc_info = kwargs.pop("exc_info", None)
        self._logger.debug(
            _structured(event, kwargs),
            exc_info=exc_info,
        )

    def info(self, event: str, **kwargs: Any) -> None:
        self._logger.info(_structured(event, kwargs))

    def warning(self, event: str, **kwargs: Any) -> None:
        self._logger.warning(_structured(event, kwargs))

    def error(self, event: str, **kwargs: Any) -> None:
        self._logger.error(_structured(event, kwargs))

    def critical(self, event: str, **kwargs: Any) -> None:
        self._logger.critical(_structured(event, kwargs))

    def exception(self, event: str, **kwargs: Any) -> None:
        self._logger.exception(_structured(event, kwargs), exc_info=True)


def _structured(event: str, kwargs: dict[str, Any]) -> dict[str, Any]:
    """Monta dict estruturado com evento + kwargs."""
    msg: dict[str, Any] = {"event": event}
    msg.update(kwargs)
    return msg


def get_domain_logger(name: str) -> DomainLogger:
    """Retorna um DomainLogger para uso em módulos de domínio."""
    return DomainLogger(name)
