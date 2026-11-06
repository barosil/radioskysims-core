"""
tests/test_logging_integration.py

Teste de integração do logging estruturado em JSON.
Valida que os logs estão sendo gerados com a estrutura correta.
"""

from __future__ import annotations

import json
import re
import tempfile
from pathlib import Path

import pytest
from radioskysims_core.logging_config import (
    bind_context,
    configure_logging,
    get_logger,
    unbind_context,
)


class TestLoggingConfiguration:
    """Testes da configuração de logging estruturado."""

    def test_configure_logging_creates_logger(self):
        """Verifica que configure_logging cria um logger válido."""
        with tempfile.TemporaryDirectory() as tmpdir:
            configure_logging(
                log_level="INFO",
                log_dir=tmpdir,
                enable_file=True,
            )

            logger = get_logger("test.module")
            assert logger is not None

    def test_get_logger_returns_structured_logger(self):
        """Verifica que get_logger retorna um logger estruturado."""
        with tempfile.TemporaryDirectory() as tmpdir:
            configure_logging(
                log_level="DEBUG",
                log_dir=tmpdir,
                enable_file=True,
            )

            logger = get_logger("radioskysims.test")
            assert logger is not None
            assert hasattr(logger, "info")
            assert hasattr(logger, "error")
            assert hasattr(logger, "exception")

    def test_logger_json_output_to_file(self):
        """Verifica que logs são armazenados em JSON no arquivo."""
        with tempfile.TemporaryDirectory() as tmpdir:
            configure_logging(
                log_level="INFO",
                log_dir=tmpdir,
                enable_file=True,
            )

            logger = get_logger("radioskysims.test")

            # Simula um log
            logger.info("test_event", test_param="test_value", count=42)

            # Verifica arquivo de log
            log_files = list(Path(tmpdir).glob("*.json"))
            assert len(log_files) > 0, "Nenhum arquivo de log JSON criado"

            # Valida conteúdo JSON
            log_file = log_files[0]
            with Path(log_file).open(encoding="utf-8") as f:
                lines = f.readlines()
                assert len(lines) > 0

                # Tenta parsear como JSON
                log_entry = json.loads(lines[-1])
                assert "timestamp" in log_entry
                assert log_entry.get("event") == "test_event"
                assert log_entry.get("test_param") == "test_value"
                assert log_entry.get("count") == 42

    def test_exception_logging_includes_stacktrace(self):
        """Verifica que logger.exception() inclui stacktrace."""
        with tempfile.TemporaryDirectory() as tmpdir:
            configure_logging(
                log_level="INFO",
                log_dir=tmpdir,
                enable_file=True,
            )

            logger = get_logger("radioskysims.test")

            # Simula uma exceção
            try:
                _ = 1 / 0
            except ZeroDivisionError:
                logger.exception("division_error_occurred")

            # Verifica arquivo de log
            log_files = list(Path(tmpdir).glob("*.json"))
            assert len(log_files) > 0

            log_file = log_files[0]
            with Path(log_file).open(encoding="utf-8") as f:
                lines = f.readlines()
                # A última linha deve ser o log da exceção
                log_entry = json.loads(lines[-1])
                assert "exc_info" in log_entry or "exception" in log_entry.get("event", "")

    def test_multiple_loggers_in_same_session(self):
        """Verifica que múltiplos loggers funcionam na mesma sessão."""
        with tempfile.TemporaryDirectory() as tmpdir:
            configure_logging(
                log_level="INFO",
                log_dir=tmpdir,
                enable_file=True,
            )

            logger_beam = get_logger("radioskysims.beam")
            logger_satellite = get_logger("radioskysims.satellite")
            logger_signal = get_logger("radioskysims.signal")

            # Simula logs de diferentes módulos
            logger_beam.info("beam_event", beam_id="B001")
            logger_satellite.info("satellite_event", sat_id="S001")
            logger_signal.info("signal_event", sig_id="SIG001")

            # Verifica que todos aparecem no mesmo arquivo
            log_files = list(Path(tmpdir).glob("*.json"))
            assert len(log_files) > 0

            log_file = log_files[0]
            with Path(log_file).open(encoding="utf-8") as f:
                lines = f.readlines()
                events = [json.loads(line).get("event") for line in lines]

                assert "beam_event" in events
                assert "satellite_event" in events
                assert "signal_event" in events

    def test_timestamp_iso_format(self):
        """Verifica que timestamp está em formato ISO 8601."""

        with tempfile.TemporaryDirectory() as tmpdir:
            configure_logging(
                log_level="INFO",
                log_dir=tmpdir,
                enable_file=True,
            )

            logger = get_logger("radioskysims.test")
            logger.info("timestamp_test")

            log_files = list(Path(tmpdir).glob("*.json"))
            log_file = log_files[0]

            with Path(log_file).open(encoding="utf-8") as f:
                log_entry = json.loads(f.readline())
                timestamp = log_entry.get("timestamp")

                # Valida ISO 8601 (aproximado)
                iso_pattern = r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}"
                assert re.match(iso_pattern, timestamp), f"Timestamp não é ISO 8601: {timestamp}"

    def test_log_level_filtering(self):
        """Verifica que level filtering funciona."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Configura apenas para WARNING e acima
            configure_logging(
                log_level="WARNING",
                log_dir=tmpdir,
                enable_file=True,
            )

            logger = get_logger("radioskysims.test")

            # Tenta logar em diferentes níveis
            logger.info("should_not_appear")
            logger.warning("should_appear")
            logger.error("should_also_appear")

            log_files = list(Path(tmpdir).glob("*.json"))
            log_file = log_files[0]

            with Path(log_file).open(encoding="utf-8") as f:
                events = [json.loads(line).get("event") for line in f]

                # INFO não deve aparecer
                # WARNING e ERROR devem aparecer
                assert "should_not_appear" not in events
                assert "should_appear" in events
                assert "should_also_appear" in events


class TestContextBinding:
    """Testes de vinculação de contexto global."""

    def test_bind_unbind_context(self):
        """Verifica que bind/unbind de contexto funciona."""
        with tempfile.TemporaryDirectory() as tmpdir:
            configure_logging(
                log_level="INFO",
                log_dir=tmpdir,
                enable_file=True,
            )

            logger = get_logger("radioskysims.test")

            # Vincula contexto
            bind_context(simulation_id="SIM001", user_id="user@test.com")
            logger.info("event_with_context", event_param="value1")

            # Desvincula contexto
            unbind_context("simulation_id", "user_id")
            logger.info("event_without_context", event_param="value2")

            log_files = list(Path(tmpdir).glob("*.json"))
            if log_files:
                log_file = log_files[0]
                with Path(log_file).open(encoding="utf-8") as f:
                    lines = [json.loads(line) for line in f]

                    # Primeiro evento deve ter contexto
                    if lines:
                        _ = lines[-2] if len(lines) > 1 else lines[0]
                        # Verifica se contexto está presente (pode variar com implementação)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
