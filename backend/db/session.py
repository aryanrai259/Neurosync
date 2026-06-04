# Purpose:      Core database setup — async engine and sessionmaker.
#               Provides the FastAPI dependency for database access.
# Called By:    API endpoints, background workers, Alembic env.py
# Calls:        core/config.py (reads database_url)
# Dependencies: sqlalchemy (ext.asyncio)

from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from backend.core.config import get_settings


def get_engine(url: str) -> AsyncEngine:
    """Creates the async SQLAlchemy engine."""
    return create_async_engine(
        url,
        echo=False,  # Set to True for SQL query logging if needed
        pool_pre_ping=True,  # Verify connections before using them
    )


# Global engine and sessionmaker instance
engine = get_engine(get_settings().database_url)

async_session = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,
)


async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    """
    FastAPI Dependency that provides a database session.
    Closes the session when the request finishes.
    """
    async with async_session() as session:
        yield session
