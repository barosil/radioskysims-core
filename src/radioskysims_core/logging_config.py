"""\
Módulo: src/radioskysims/infrastructure/logging_config.py

Descrição:
    Configuração centralizada de logging estruturado em JSON com suporte
    para contexto global e eventos de HTTP/IO/DB.

Copyright BINGO Collaboration
Last modified: 2026-03-03
"""

from __future__ import annotations

import json
import logging
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any


class JSONFormatter(logging.Formatter):
    """Formata logs como JSON estruturado."""

    def __init__(self) -> None:
        super().__init__()
        self._context: dict[str, Any] = {}

    def format(self, record: logging.LogRecord) -> str:
        """Converte LogRecord para JSON."""
        log_obj = {
            "timestamp": datetime.fromtimestamp(record.created, tz=UTC).isoformat(),
            "level": record.levelname,
            "logger": record.name,
        }

        # Se msg for dict, usa como base
        if isinstance(record.msg, dict):
            log_obj.update(record.msg)
        else:
            # Caso contrário, tenta obter a mensagem
            log_obj["event"] = record.getMessage()

        # Adiciona argumentos extras se for dict
        if record.args and isinstance(record.args, dict):
            log_obj.update(record.args)

        # Adiciona exceção se houver
        if record.exc_info:
            log_obj["exc_info"] = self.formatException(record.exc_info)

        # Adiciona contexto global
        log_obj.update(self._context)

        return json.dumps(log_obj, ensure_ascii=False, default=str)

    def set_context(self, **context: Any) -> None:
        """Define contexto global para todos os logs."""
        self._context.update(context)

    def clear_context(self, *keys: str) -> None:
        """Remove chaves do contexto."""
        for key in keys:
            self._context.pop(key, None)


# Singleton global para manter estado do formatador
_json_formatter = JSONFormatter()
_file_handlers: dict[str, logging.FileHandler] = {}


def _setup_file_handler(log_dir: str = "logs") -> str:
    """
    Configura handler de arquivo para logs.

    Args:
        log_dir: Diretório onde armazenar logs.

    Returns:
        Caminho completo do arquivo de log.
    """
    log_path = Path(log_dir)
    log_path.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_file = log_path / f"radioskysim_{timestamp}.json"
    return str(log_file)


def _configure_stdlib_logging(
    log_level: str = "INFO",
    log_file: str | None = None,
) -> None:
    """
    Configura logging padrão da stdlib com JSON estruturado.

    Args:
        log_level: Nível mínimo de log (DEBUG, INFO, WARNING, ERROR, CRITICAL).
        log_file: Caminho do arquivo de log (opcional).
    """
    # Converte string de level para int
    level = getattr(logging, log_level.upper(), logging.INFO)

    # Silencia loggers verbosos
    logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)
    logging.getLogger("matplotlib").setLevel(logging.WARNING)
    logging.getLogger("skyfield").setLevel(logging.WARNING)
    logging.getLogger("scipy").setLevel(logging.WARNING)

    root_logger = logging.getLogger()
    root_logger.setLevel(level)
    # Fecha handlers antigos antes de trocar (evita FileHandler órfão → ResourceWarning)
    for h in root_logger.handlers[:]:
        root_logger.removeHandler(h)
        try:
            h.close()
        except Exception:
            pass
    root_logger.setLevel(level)

    stream_handler = logging.StreamHandler(stream=sys.stdout)
    stream_handler.setLevel(level)
    stream_handler.setFormatter(_json_formatter)
    root_logger.addHandler(stream_handler)

    if log_file:
        file_handler = logging.FileHandler(log_file, encoding="utf-8")
        file_handler.setLevel(level)
        file_handler.setFormatter(_json_formatter)
        root_logger.addHandler(file_handler)
        _file_handlers[log_file] = file_handler


def configure_logging(
    log_level: str = "INFO",
    log_dir: str = "logs",
    enable_file: bool = True,
) -> None:
    """
    Configura o sistema de logging global com JSON estruturado.

    Deve ser chamado UMA VEZ no início da aplicação (ex: main.py, conftest.py).

    Args:
        log_level: Nível mínimo (DEBUG, INFO, WARNING, ERROR, CRITICAL).
        log_dir: Diretório para armazenar logs em arquivo.
        enable_file: Se True, cria arquivo de log.

    Exemplo:
        from radioskysims_core.logging_config import configure_logging

        if __name__ == "__main__":
            configure_logging(log_level="INFO", enable_file=True)
            # ... resto da aplicação
    """
    log_file = _setup_file_handler(log_dir) if enable_file else None
    _configure_stdlib_logging(log_level=log_level, log_file=log_file)


class StructuredLogger:
    """Logger que aceita kwargs para logging estruturado."""

    def __init__(self, logger: logging.Logger) -> None:
        self._logger = logger

    def _log(self, level: int, event: str, **kwargs: Any) -> None:
        """Log com evento e kwargs estruturados."""
        # Cria um dict com o evento e kwargs
        msg_dict = {"event": event}
        msg_dict.update(kwargs)

        # Passa o dict diretamente para que JSONFormatter o processe
        self._logger.log(level, msg_dict)

    def debug(self, event: str, **kwargs: Any) -> None:
        """Log com nível DEBUG."""
        self._log(logging.DEBUG, event, **kwargs)

    def info(self, event: str, **kwargs: Any) -> None:
        """Log com nível INFO."""
        self._log(logging.INFO, event, **kwargs)

    def warning(self, event: str, **kwargs: Any) -> None:
        """Log com nível WARNING."""
        self._log(logging.WARNING, event, **kwargs)

    def error(self, event: str, **kwargs: Any) -> None:
        """Log com nível ERROR."""
        self._log(logging.ERROR, event, **kwargs)

    def critical(self, event: str, **kwargs: Any) -> None:
        """Log com nível CRITICAL."""
        self._log(logging.CRITICAL, event, **kwargs)

    def exception(self, event: str, **kwargs: Any) -> None:
        """Log com nível ERROR e exc_info."""
        # Não usa _log para que exc_info seja capturado corretamente
        msg_dict = {"event": event}
        msg_dict.update(kwargs)
        self._logger.exception(msg_dict, exc_info=True)


def get_logger(name: str) -> StructuredLogger:
    """
    Obtém um logger estruturado para um módulo.

    Args:
        name: Nome do módulo/componente (ex: "radioskysims.beam").

    Returns:
        Logger estruturado com suporte a kwargs.

    Exemplo:
        logger = get_logger("radioskysims.beam")
        logger.info("beam_created", beam_id="BEAM001", frequency_ghz=10.5)
        logger.warning("beam_interpolation_slow", duration_ms=2500)
        logger.error("beam_load_failed", path="/path/to/beam", reason="file_not_found")
    """
    return StructuredLogger(logging.getLogger(name))


def log_http_event(
    logger: StructuredLogger,
    event: str,
    method: str,
    url: str,
    status_code: int | None = None,
    duration_ms: float | None = None,
    **kwargs: Any,
) -> None:
    """Registra evento HTTP em formato estruturado."""
    logger.info(
        event,
        category="http",
        method=method,
        url=url,
        status_code=status_code,
        duration_ms=duration_ms,
        **kwargs,
    )


def log_io_event(
    logger: StructuredLogger,
    event: str,
    operation: str,
    path: str,
    bytes_count: int | None = None,
    **kwargs: Any,
) -> None:
    """Registra evento de IO em formato estruturado."""
    logger.info(
        event,
        category="io",
        operation=operation,
        path=path,
        bytes_count=bytes_count,
        **kwargs,
    )


def log_db_event(
    logger: StructuredLogger,
    event: str,
    operation: str,
    table: str | None = None,
    duration_ms: float | None = None,
    **kwargs: Any,
) -> None:
    """Registra evento de banco em formato estruturado."""
    logger.info(
        event,
        category="db",
        operation=operation,
        table=table,
        duration_ms=duration_ms,
        **kwargs,
    )


# ===================================================================
# Atalhos para sintaxe mais concisa
# ===================================================================


def bind_context(**context: Any) -> None:
    """
    Vincula contexto global aos logs subsequentes.

    Útil para adicionar informações que serão incluídas em todos os logs
    (ex: request_id, user_id, session_id).

    Args:
        **context: Pares key=value para vincular.

    Exemplo:
        bind_context(simulation_id="SIM001", user_id="USER123")
        logger = get_logger("radioskysims.simulation")
        logger.info("simulation_started")  # Incluirá simulation_id e user_id
    """
    _json_formatter.set_context(**context)


def unbind_context(*keys: str) -> None:
    """Remove chaves do contexto global."""
    _json_formatter.clear_context(*keys)
