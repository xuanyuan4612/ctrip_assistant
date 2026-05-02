"""酒店/租车/旅行 ORM 模型"""
from datetime import date, datetime
from typing import Optional

from sqlalchemy import String, Integer, Boolean, Text, Date
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import DBModelBase


class HotelModel(DBModelBase):
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    location: Mapped[Optional[str]] = mapped_column(String(100), nullable=True, index=True)
    price_tier: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    checkin_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    checkout_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    booked: Mapped[bool] = mapped_column(Boolean, default=False)


class CarRentalModel(DBModelBase):
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    location: Mapped[Optional[str]] = mapped_column(String(100), nullable=True, index=True)
    price_tier: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    start_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    end_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    booked: Mapped[bool] = mapped_column(Boolean, default=False)


class TripRecommendationModel(DBModelBase):
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    location: Mapped[Optional[str]] = mapped_column(String(100), nullable=True, index=True)
    keywords: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    details: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    booked: Mapped[bool] = mapped_column(Boolean, default=False)
