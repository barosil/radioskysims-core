# infrastructure/db/engine.py
from __future__ import annotations

import logging
from urllib.parse import quote_plus

from sqlalchemy import Engine, inspect
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import sessionmaker
from sqlmodel import Session, SQLModel, create_engine, select

from radioskysims_core.config.config_loader import load_config
from radioskysims_core.logging_config import get_logger, log_db_event

logger = logging.getLogger(__name__)
slogger = get_logger(__name__)

# ==== Configuração via TOML ====
ENV = load_config(key="DB")
POSTGRES_USER = ENV.get("POSTGRES_USER", "radio")
POSTGRES_PASSWORD = ENV.get("POSTGRES_PASSWORD", "radio")
POSTGRES_HOST = ENV.get("POSTGRES_HOST", "localhost")
POSTGRES_PORT = ENV.get("POSTGRES_PORT", 5432)
POSTGRES_DB = ENV.get("POSTGRES_DB", "radioskysims")


class Database:
    def __init__(self, model: SQLModel | None = None) -> None:
        self.credentials = {
            "POSTGRES_USER": POSTGRES_USER,
            "POSTGRES_PASSWORD": POSTGRES_PASSWORD,
            "POSTGRES_HOST": POSTGRES_HOST,
            "POSTGRES_PORT": POSTGRES_PORT,
            "POSTGRES_DB": POSTGRES_DB,
        }
        self.db = f"{self.credentials['POSTGRES_HOST']}:{self.credentials['POSTGRES_PORT']}"
        self.uri = self._build_uri()
        self.model = model
        self.engine = self._create_engine()
        self._sessionmaker = sessionmaker(self.engine, class_=Session, expire_on_commit=False)

    # =========================================================
    # Engine / URI
    # =========================================================
    def __repr__(self) -> str:
        """
        Retorna uma representação legível do estado atual do engine de banco de dados.

        Mostra:
            - URL sanitizada (sem credenciais)
            - Dialeto e driver SQLAlchemy
            - Lista de tabelas disponíveis no schema atual
        """

        if not hasattr(self, "engine") or self.engine is None:
            return "<Database Engine (não inicializado)>"

        # Extrai informações da URL
        url = str(self.engine.url)
        if "@" in url:  # remove credenciais
            url = url.split("@")[-1]
        url = url.replace("+psycopg", "").replace("+asyncpg", "")

        dialect = self.engine.url.get_dialect().name
        driver = self.engine.url.get_driver_name()

        # Tenta inspecionar as tabelas
        try:
            inspector = inspect(self.engine)
            tables = inspector.get_table_names()
            tables_list = ", ".join(tables) if tables else "— nenhuma tabela encontrada —"
        except Exception as e:
            tables_list = f"⚠️ erro ao inspecionar ({type(e).__name__}: {e})"

        header = f"<Database Engine — {dialect}+{driver}>"
        line = "─" * len(header)

        return f"{header}\n{line}\nURL: {url}\nTabelas: {tables_list}\n"

    def session(self) -> Session:
        """Context manager para criar uma sessão."""
        return self._sessionmaker()

    def _build_uri(self) -> str:
        """Monta a URI de conexão para o PostgreSQL."""
        return (
            f"postgresql+psycopg2://{self.credentials['POSTGRES_USER']}:"
            f"{quote_plus(self.credentials['POSTGRES_PASSWORD'])}"
            f"@{self.db}/{self.credentials['POSTGRES_DB']}"
        )

    def _create_engine(self) -> Engine:
        """Cria engine única para a instância Database."""
        logger.debug("Criando engine para %s", self.db)
        log_db_event(slogger, "db_engine_create", operation="connect", table=None)
        return create_engine(self.uri, echo=False, future=True)

    def close(self) -> None:
        """Fecha a engine."""
        try:
            self.engine.dispose()
            logger.info("Engine fechada com sucesso.")
            log_db_event(slogger, "db_engine_close", operation="disconnect", table=None)
        except SQLAlchemyError as e:
            logger.error("Erro ao fechar a engine: %s", e)
            raise

    def clear_db(self) -> None:
        """Deleta todas as tabelas do banco."""
        try:
            SQLModel.metadata.drop_all(self.engine)
            logger.info("Todas as tabelas foram deletadas do banco.")
            log_db_event(slogger, "db_clear", operation="drop_all", table="*")
        except SQLAlchemyError as e:
            logger.error("Erro ao limpar o banco de dados: %s", e)
            raise

    def test_connection(self) -> bool:
        """Testa a conexão com o banco de dados."""
        try:
            with self.session() as session:
                session.exec(select(1))
            logger.info("Conexão com o banco de dados bem-sucedida.")
            log_db_event(slogger, "db_connection_ok", operation="select", table="healthcheck")
            return True
        except SQLAlchemyError as e:
            logger.error("Erro ao conectar ao banco de dados: %s", e)
            log_db_event(
                slogger,
                "db_connection_error",
                operation="select",
                table="healthcheck",
                error=str(e),
            )
            return False

    # =========================================================
    # DDL
    # =========================================================
    def create_table(self, model: SQLModel | None = None) -> None:
        """Cria tabelas no banco com base no modelo fornecido."""
        mdl = model or self.model
        if not mdl:
            msg = "Nenhum modelo fornecido para criação de tabela."
            raise ValueError(msg)
        try:
            # use SQLModel.metadata to ensure correct metadata is used
            SQLModel.metadata.create_all(self.engine)
            logger.info("Tabela criada para modelo %s", getattr(mdl, "__tablename__", str(mdl)))
            log_db_event(
                slogger,
                "db_create_table",
                operation="create_all",
                table=getattr(mdl, "__tablename__", str(mdl)),
            )
        except SQLAlchemyError as e:
            logger.error("Erro ao criar tabela para %s: %s", mdl, e)
            raise

    def drop_table(self, model: SQLModel | None = None) -> None:
        """Deleta tabelas no banco com base no modelo fornecido."""
        mdl = model or self.model
        if not mdl:
            msg = "Nenhum modelo fornecido para deleção de tabela."
            raise ValueError(msg)
        try:
            SQLModel.metadata.drop_all(self.engine)
            logger.info(
                "Tabela deletada para modelo %s",
                getattr(mdl, "__tablename__", str(mdl)),
            )
            log_db_event(
                slogger,
                "db_drop_table",
                operation="drop_all",
                table=getattr(mdl, "__tablename__", str(mdl)),
            )
        except SQLAlchemyError as e:
            logger.error("Erro ao deletar tabela para %s: %s", mdl, e)
            raise


# =========================================================
