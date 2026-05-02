"""Declarative base for all ORM models in the app.db package."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, MetaData, func
from sqlalchemy.orm import DeclarativeBase, declared_attr, Mapped, mapped_column


_convention: dict[str, str] = {
    "ix": "ix_%(column_0_label)s",
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}


class DBModelBase(DeclarativeBase):
    """Abstract base for all application ORM models."""

    metadata = MetaData(naming_convention=_convention)

    @declared_attr.directive
    def __tablename__(cls) -> str:
        return f"t_{cls.__name__.lower()}"

    __table_args__ = {"mysql_engine": "InnoDB"}
    __mapper_args__ = {"eager_defaults": True}

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    create_time: Mapped[datetime] = mapped_column(DateTime, insert_default=func.now(), nullable=False, comment="\u8bb0\u5f55\u521b\u5efa\u65f6\u95f4")
    update_time: Mapped[datetime] = mapped_column(DateTime, insert_default=func.now(), onupdate=func.now(), nullable=False, comment="\u8bb0\u5f55\u6700\u540e\u4fee\u6539\u65f6\u95f4")
