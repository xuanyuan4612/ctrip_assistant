"""Database access layer - async MySQL engine + declarative base."""

from app.db.engine_mysql import engine
from app.db.base import DBModelBase

__all__ = [
    "engine",
    "DBModelBase",
]
