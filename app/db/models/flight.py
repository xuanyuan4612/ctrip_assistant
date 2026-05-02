"""航班 ORM 模型"""
from datetime import datetime
from typing import Optional

from sqlalchemy import String, DateTime, Integer, Boolean, Float, Text, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import DBModelBase


class FlightModel(DBModelBase):
    flight_no: Mapped[str] = mapped_column(String(10), nullable=False, index=True)
    departure_airport: Mapped[str] = mapped_column(String(10), nullable=False, index=True)
    arrival_airport: Mapped[str] = mapped_column(String(10), nullable=False, index=True)
    scheduled_departure: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    scheduled_arrival: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    actual_departure: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    actual_arrival: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    status: Mapped[str] = mapped_column(String(20), default="Scheduled")


class TicketModel(DBModelBase):
    ticket_no: Mapped[str] = mapped_column(String(13), unique=True, nullable=False, index=True)
    book_ref: Mapped[str] = mapped_column(String(10), nullable=False)
    passenger_id: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    passenger_name: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)


class TicketFlightModel(DBModelBase):
    ticket_no: Mapped[str] = mapped_column(String(13), ForeignKey("t_ticketmodel.ticket_no"), nullable=False, index=True)
    flight_id: Mapped[int] = mapped_column(Integer, ForeignKey("t_flightmodel.id"), nullable=False, index=True)
    fare_conditions: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    amount: Mapped[Optional[float]] = mapped_column(Float, nullable=True)


class BoardingPassModel(DBModelBase):
    ticket_no: Mapped[str] = mapped_column(String(13), ForeignKey("t_ticketmodel.ticket_no"), nullable=False)
    flight_id: Mapped[int] = mapped_column(Integer, ForeignKey("t_flightmodel.id"), nullable=False)
    boarding_no: Mapped[int] = mapped_column(Integer, nullable=False)
    seat_no: Mapped[Optional[str]] = mapped_column(String(5), nullable=True)
