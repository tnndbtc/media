"""Async SQLAlchemy engine and Base class."""

from functools import lru_cache

from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from app.config.settings import get_settings


class Base(DeclarativeBase):
    """SQLAlchemy declarative base class."""

    pass


@lru_cache
def get_engine() -> AsyncEngine:
    """Get cached async SQLAlchemy engine.

    Returns:
        AsyncEngine configured for SQLite
    """
    settings = get_settings()
    database_url = settings.database_url

    # Convert sqlite:// to sqlite+aiosqlite://
    if database_url.startswith("sqlite://"):
        database_url = database_url.replace("sqlite://", "sqlite+aiosqlite://", 1)

    return create_async_engine(
        database_url,
        echo=settings.debug,
        future=True,
    )


async def init_db() -> None:
    """Initialize database and create tables."""
    # Import models to register them with Base.metadata
    from app.db.models import Prompt  # noqa: F401

    engine = get_engine()
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def close_db() -> None:
    """Close database connections."""
    engine = get_engine()
    await engine.dispose()
