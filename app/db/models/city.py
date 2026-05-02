"""城市 ORM 模型"""
from typing import Optional

from sqlalchemy import String, Boolean, JSON
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import DBModelBase


class CityModel(DBModelBase):
    name_zh: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    name_en: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    name_aliases: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    iata_code: Mapped[Optional[str]] = mapped_column(String(5), nullable=True, index=True)
    country: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    timezone: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
