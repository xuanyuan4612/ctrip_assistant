"""Async MySQL engine with connection pooling."""

from __future__ import annotations

import logging

from sqlalchemy import URL
from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine

from config import settings

logger: logging.Logger = logging.getLogger(__name__)


def _build_async_url() -> URL:
    driver: str = settings.DATABASE.DRIVER
    async_driver: str = f"{driver}+aiomysql" if "+" not in driver else driver
    query: dict | None = settings.DATABASE.get("QUERY", None)
    if query is None:
        query = {"charset": "utf8mb4"}
    return URL(
        drivername=async_driver,
        username=settings.DATABASE.get("USERNAME", None),
        password=settings.DATABASE.get("PASSWORD", None),
        host=settings.DATABASE.get("HOST", None),
        port=settings.DATABASE.get("PORT", None),
        database=settings.DATABASE.get("NAME", None),
        query=query,
    )


_ASYNC_DATABASE_URL: URL = _build_async_url()

engine: AsyncEngine = create_async_engine(
    url=_ASYNC_DATABASE_URL,
    pool_size=20,
    max_overflow=10,
    pool_pre_ping=True,
    pool_recycle=3600,
    echo=logger.isEnabledFor(logging.DEBUG),
    future=True,
)

logger.info(
    "Async MySQL engine created \u2014 pool_size=20, max_overflow=10, url=%s",
    _ASYNC_DATABASE_URL.render_as_string(hide_password=True),
)
