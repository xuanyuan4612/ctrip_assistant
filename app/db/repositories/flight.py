"""Flight repository - search, manage tickets, update/cancel bookings."""
from __future__ import annotations

import logging
from datetime import date, datetime
from typing import Dict, List, Optional

from sqlalchemy import String, and_, select, text
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Mapped, mapped_column

from app.core.exceptions import NotFoundError
from app.db.models.business_base import BusinessBase
from app.db.repositories.base import AsyncBaseRepository

logger = logging.getLogger(__name__)


class FlightModel(BusinessBase):
    __tablename__ = "flights"

    flight_id: Mapped[int] = mapped_column(primary_key=True, autoincrement=False)
    flight_no: Mapped[str] = mapped_column(String(10))
    scheduled_departure: Mapped[Optional[str]] = mapped_column(String(50))
    scheduled_arrival: Mapped[Optional[str]] = mapped_column(String(50))
    departure_airport: Mapped[Optional[str]] = mapped_column(String(10))
    arrival_airport: Mapped[Optional[str]] = mapped_column(String(10))
    status: Mapped[Optional[str]] = mapped_column(String(20))
    aircraft_code: Mapped[Optional[str]] = mapped_column(String(10))
    actual_departure: Mapped[Optional[str]] = mapped_column(String(50))
    actual_arrival: Mapped[Optional[str]] = mapped_column(String(50))


class TicketModel(BusinessBase):
    __tablename__ = "tickets"

    ticket_no: Mapped[str] = mapped_column(String(13), primary_key=True)
    book_ref: Mapped[Optional[str]] = mapped_column(String(10))
    passenger_id: Mapped[Optional[str]] = mapped_column(String(20))


class TicketFlightModel(BusinessBase):
    __tablename__ = "ticket_flights"

    ticket_no: Mapped[str] = mapped_column(String(13), primary_key=True)
    flight_id: Mapped[int] = mapped_column(primary_key=True, autoincrement=False)
    fare_conditions: Mapped[Optional[str]] = mapped_column(String(20))
    amount: Mapped[Optional[int]] = mapped_column()


class BoardingPassModel(BusinessBase):
    __tablename__ = "boarding_passes"

    ticket_no: Mapped[str] = mapped_column(String(13), primary_key=True)
    flight_id: Mapped[int] = mapped_column(primary_key=True, autoincrement=False)
    boarding_no: Mapped[Optional[int]] = mapped_column()
    seat_no: Mapped[Optional[str]] = mapped_column(String(5))


class FlightRepository(AsyncBaseRepository[FlightModel]):
    """Async repository for flight search and ticket management."""

    def __init__(self) -> None:
        super().__init__(FlightModel)

    async def search(
        self,
        session: AsyncSession,
        departure_airport: Optional[str] = None,
        arrival_airport: Optional[str] = None,
        start_time: Optional[date | datetime] = None,
        end_time: Optional[date | datetime] = None,
        limit: int = 20,
    ) -> List[Dict]:
        """Search flights by departure/arrival airport and time range."""
        stmt = select(FlightModel).where(1 == 1)
        if departure_airport:
            stmt = stmt.where(FlightModel.departure_airport == departure_airport)
        if arrival_airport:
            stmt = stmt.where(FlightModel.arrival_airport == arrival_airport)
        if start_time:
            stmt = stmt.where(FlightModel.scheduled_departure >= str(start_time))
        if end_time:
            stmt = stmt.where(FlightModel.scheduled_departure <= str(end_time))
        stmt = stmt.limit(limit)
        result = await session.execute(stmt)
        return [_row_to_dict(r) for r in result.scalars().all()]

    async def get_tickets_by_passenger(
        self,
        session: AsyncSession,
        passenger_id: str,
    ) -> List[Dict]:
        """Return all tickets (with flight + boarding-pass details) for a passenger."""
        query = text("""
            SELECT
                t.ticket_no, t.book_ref,
                f.flight_id, f.flight_no, f.departure_airport, f.arrival_airport,
                f.scheduled_departure, f.scheduled_arrival,
                bp.seat_no, tf.fare_conditions
            FROM tickets t
                JOIN ticket_flights tf ON t.ticket_no = tf.ticket_no
                JOIN flights f ON tf.flight_id = f.flight_id
                JOIN boarding_passes bp ON bp.ticket_no = t.ticket_no
                    AND bp.flight_id = f.flight_id
            WHERE t.passenger_id = :passenger_id
        """)
        result = await session.execute(query, {"passenger_id": passenger_id})
        columns = result.keys()
        return [dict(zip(columns, row)) for row in result.fetchall()]

    async def update_ticket_flight(
        self,
        session: AsyncSession,
        ticket_no: str,
        new_flight_id: int,
        passenger_id: str,
    ) -> Dict:
        """Reassign a ticket to a new flight with ownership verification."""
        new_flight = await session.get(FlightModel, new_flight_id)
        if new_flight is None:
            raise NotFoundError(f"Provided new flight ID {new_flight_id} is invalid.")

        tf_result = await session.execute(
            select(TicketFlightModel).where(
                TicketFlightModel.ticket_no == ticket_no
            )
        )
        if tf_result.scalar_one_or_none() is None:
            raise NotFoundError(f"Ticket {ticket_no} not found in ticket_flights.")

        ticket_result = await session.execute(
            select(TicketModel).where(
                and_(
                    TicketModel.ticket_no == ticket_no,
                    TicketModel.passenger_id == passenger_id,
                )
            )
        )
        if ticket_result.scalar_one_or_none() is None:
            raise NotFoundError(
                f"Passenger {passenger_id} is not the owner of ticket {ticket_no}."
            )

        await session.execute(
            text("UPDATE ticket_flights SET flight_id = :new_fid WHERE ticket_no = :tno"),
            {"new_fid": new_flight_id, "tno": ticket_no},
        )
        await session.commit()
        logger.info("Ticket %s reassigned to flight %s", ticket_no, new_flight_id)
        return {"success": True, "message": "Ticket successfully updated.", "ticket_no": ticket_no, "new_flight_id": new_flight_id}

    async def cancel_ticket(
        self,
        session: AsyncSession,
        ticket_no: str,
        passenger_id: str,
    ) -> Dict:
        """Cancel a ticket with ownership verification."""
        tf_result = await session.execute(
            select(TicketFlightModel).where(
                TicketFlightModel.ticket_no == ticket_no
            )
        )
        if tf_result.scalar_one_or_none() is None:
            raise NotFoundError(f"Ticket {ticket_no} not found.")

        ticket_result = await session.execute(
            select(TicketModel).where(
                and_(
                    TicketModel.ticket_no == ticket_no,
                    TicketModel.passenger_id == passenger_id,
                )
            )
        )
        if ticket_result.scalar_one_or_none() is None:
            raise NotFoundError(
                f"Passenger {passenger_id} is not the owner of ticket {ticket_no}."
            )

        await session.execute(
            text("DELETE FROM ticket_flights WHERE ticket_no = :tno"),
            {"tno": ticket_no},
        )
        await session.commit()
        logger.info("Ticket %s cancelled by passenger %s", ticket_no, passenger_id)
        return {"success": True, "message": "Ticket successfully cancelled.", "ticket_no": ticket_no}


def _row_to_dict(row: object) -> Dict:
    return {c.key: getattr(row, c.key) for c in row.__table__.columns}


__all__ = ["FlightRepository"]
