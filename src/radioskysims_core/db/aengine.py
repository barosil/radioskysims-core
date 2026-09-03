"""
Módulo: src/radioskysims/infrastructure/db/aengine.py

Descrição:
    Engine assíncrono SQLAlchemy para conexão com PostgreSQL.
    Fornece configuração, sessões assíncronas e funções utilitárias
    para gerenciamento do banco de dados.
"""

# infrastructure/db/engine.py
# infrastructure/db/engine.py
from __future__ import annotations

import logging
from collections.abc import AsyncGenerator
from urllib.parse import quote_plus

from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlmodel import SQLModel, select

from radioskysims_core.config.config_loader import load_config
from radioskysims_core.logging_config import get_logger, log_db_event

logger = logging.getLogger(__name__)
slogger = get_logger(__name__)

# =========================================================
# Configuração via arquivo TOML
# =========================================================
ENV = load_config(key="DB")

POSTGRES_USER = ENV.get("POSTGRES_USER", "radio")
POSTGRES_PASSWORD = ENV.get("POSTGRES_PASSWORD", "radio")
POSTGRES_HOST = ENV.get("POSTGRES_HOST", "localhost")
POSTGRES_PORT = ENV.get("POSTGRES_PORT", 5432)
POSTGRES_DB = ENV.get("POSTGRES_DB", "radioskysims")


# =========================================================
# Criação do Engine assíncrono
# =========================================================
def build_async_uri() -> str:
    """
    Constrói a URI de conexão para PostgreSQL com driver assíncrono.

    Monta a string de conexão usando asyncpg, adequada para SQLAlchemy assíncrono.
    Credenciais são carregadas do arquivo de configuração TOML.

    Returns:
        str: URI de conexão PostgreSQL no formato:
            postgresql+asyncpg://user:password@host:port/database

    Notes:
        A senha é codificada com quote_plus para permitir caracteres especiais.
    """
    return (
        f"postgresql+asyncpg://{POSTGRES_USER}:"
        f"{quote_plus(POSTGRES_PASSWORD)}@"
        f"{POSTGRES_HOST}:{POSTGRES_PORT}/{POSTGRES_DB}"
    )


ASYNC_DATABASE_URI = build_async_uri()

# Engine async LAZY: nada é criado no import (evita ruído no startup de CLIs e
# notebooks que não usam banco async — auditoria de UX, item R1). A engine só é
# criada no primeiro uso real; asyncpg é opcional (extra de banco).
async_engine: AsyncEngine | None = None
AsyncSessionLocal: async_sessionmaker[AsyncSession] | None = None


def _ensure_async_engine() -> tuple[AsyncEngine, async_sessionmaker[AsyncSession]]:
    """Cria (sob demanda) e cacheia a engine async + sessionmaker.

    Raises:
        RuntimeError: se o driver async (asyncpg) não estiver instalado —
            apenas quando o banco async é realmente utilizado.
    """
    global async_engine, AsyncSessionLocal

    if async_engine is None or AsyncSessionLocal is None:
        try:
            engine = create_async_engine(
                ASYNC_DATABASE_URI,
                echo=False,  # pode ativar True para debug
                future=True,
                pool_pre_ping=True,
            )
        except ModuleNotFoundError as exc:
            msg = (
                "asyncpg não está instalado no ambiente; instale o extra de "
                "banco assíncrono (ex.: radioskysim[db]) para usar a engine async."
            )
            raise RuntimeError(msg) from exc
        async_engine = engine
        AsyncSessionLocal = async_sessionmaker(
            engine,
            expire_on_commit=False,
            class_=AsyncSession,
        )

    # Garantia por construção: se chegou aqui, ambas estão definidas.
    assert async_engine is not None and AsyncSessionLocal is not None
    return async_engine, AsyncSessionLocal


# =========================================================
# Contexto de sessão
# =========================================================
async def get_session() -> AsyncGenerator[AsyncSession, None]:
    """
    Gerador de sessão assíncrona para uso em repositórios ou dependências.

    Fornece uma sessão SQLAlchemy assíncrona com gerenciamento automático
    de transações e rollback em caso de erro.

    Yields:
        AsyncSession: Sessão assíncrona ativa.

    Raises:
        SQLAlchemyError: Propaga erros de banco de dados após rollback.

    Examples:
        >>> async for session in get_session():
        ...     result = await session.execute(select(Satellite))
    """
    _, session_local = _ensure_async_engine()
    async with session_local() as session:
        try:
            yield session
        except SQLAlchemyError as e:
            logger.error("Erro na sessão: %s", e)
            await session.rollback()
            raise
        finally:
            await session.close()


# =========================================================
# Funções utilitárias do banco
# =========================================================
async def init_db() -> None:
    """Cria todas as tabelas no banco (DDL)."""
    engine, _ = _ensure_async_engine()
    async with engine.begin() as conn:
        await conn.run_sync(SQLModel.metadata.create_all)
    logger.info("✅ Tabelas criadas com sucesso.")
    log_db_event(slogger, "adb_init", operation="create_all", table="*")


async def clear_db() -> None:
    """Remove todas as tabelas (DANGER: use com cautela)."""
    engine, _ = _ensure_async_engine()
    async with engine.begin() as conn:
        await conn.run_sync(SQLModel.metadata.drop_all)
    logger.warning("⚠️ Todas as tabelas foram removidas do banco!")
    log_db_event(slogger, "adb_clear", operation="drop_all", table="*")


async def test_connection() -> bool:
    """Testa a conexão com o banco de dados."""
    try:
        engine, _ = _ensure_async_engine()
        async with engine.connect() as conn:
            result = await conn.execute(select(1))
            _ = result.scalar()
        logger.info("Conexão com o banco de dados bem-sucedida.")
        log_db_event(slogger, "adb_connection_ok", operation="select", table="healthcheck")
        return True
    except SQLAlchemyError as e:
        logger.error("Erro ao conectar ao banco: %s", e)
        log_db_event(
            slogger,
            "adb_connection_error",
            operation="select",
            table="healthcheck",
            error=str(e),
        )
        return False


# End of file: src/radioskysims/infrastructure/db/engine.py
