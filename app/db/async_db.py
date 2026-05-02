"""Async SQLAlchemy engine and session factory for the business SQLite database."""
from __future__ import annotations

import logging
from pathlib import Path
from typing import AsyncGenerator

from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

logger = logging.getLogger(__name__)

_SQLITE_PATH = str(
    Path(__file__).resolve().parent.parent.parent / "travel_new.sqlite"
)

async_engine = create_async_engine(
    f"sqlite+aiosqlite:///{_SQLITE_PATH}",
    echo=False,
    future=True,
    connect_args={"check_same_thread": False},
)

AsyncSessionLocal = async_sessionmaker(
    bind=async_engine,
    class_=AsyncSession,
    autoflush=True,
    expire_on_commit=False,
)


async def get_async_session() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI-compatible async session dependency."""
    async with AsyncSessionLocal() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise


async def init_db() -> None:
    from app.db.models.business_base import BusinessBase
    async with async_engine.begin() as conn:
        await conn.run_sync(BusinessBase.metadata.create_all)


__all__ = [
    "async_engine",
    "AsyncSessionLocal",
    "get_async_session",
    "init_db",
]
