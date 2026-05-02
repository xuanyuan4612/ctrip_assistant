"""Hotel repository - search, book, update, and cancel hotel reservations."""
from __future__ import annotations

import logging
from datetime import date, datetime
from typing import Dict, List, Optional, Union

from sqlalchemy import String, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Mapped, mapped_column

from app.core.exceptions import NotFoundError
from app.db.models.business_base import BusinessBase
from app.db.repositories.base import AsyncBaseRepository

logger = logging.getLogger(__name__)


class HotelModel(BusinessBase):
    __tablename__ = "hotels"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[Optional[str]] = mapped_column(String(100))
    location: Mapped[Optional[str]] = mapped_column(String(100))
    price_tier: Mapped[Optional[str]] = mapped_column(String(20))
    checkin_date: Mapped[Optional[str]] = mapped_column(String(20))
    checkout_date: Mapped[Optional[str]] = mapped_column(String(20))
    booked: Mapped[Optional[int]] = mapped_column(default=0)


class HotelRepository(AsyncBaseRepository[HotelModel]):
    """Async repository for hotel search and reservation management."""

    def __init__(self) -> None:
        super().__init__(HotelModel)

    async def search(
        self,
        session: AsyncSession,
        location: Optional[str] = None,
        name: Optional[str] = None,
    ) -> List[Dict]:
        """Search hotels by location and/or name (LIKE match)."""
        stmt = select(HotelModel).where(1 == 1)
        if location:
            stmt = stmt.where(HotelModel.location.like(f"%{location}%"))
        if name:
            stmt = stmt.where(HotelModel.name.like(f"%{name}%"))
        result = await session.execute(stmt)
        return [_row_to_dict(r) for r in result.scalars().all()]

    async def book(
        self,
        session: AsyncSession,
        hotel_id: int,
        user_id: int | str,
    ) -> Dict:
        """Book a hotel by setting booked = 1."""
        obj = await self.get_by_id_or_raise(
            session, hotel_id,
            detail=f"Hotel with id={hotel_id} not found.",
        )
        obj.booked = 1
        await session.commit()
        await session.refresh(obj)
        logger.info("Hotel %s booked by user %s", hotel_id, user_id)
        return _row_to_dict(obj)

    async def update(
        self,
        session: AsyncSession,
        hotel_id: int,
        **kwargs: Union[str, date, datetime, None],
    ) -> Dict:
        """Update arbitrary fields on a hotel record."""
        obj = await self.get_by_id_or_raise(
            session, hotel_id,
            detail=f"Hotel with id={hotel_id} not found.",
        )
        changed = []
        for key, value in kwargs.items():
            if value is not None and hasattr(obj, key):
                setattr(obj, key, str(value) if isinstance(value, (date, datetime)) else value)
                changed.append(key)
        if not changed:
            raise ValueError("No fields provided for update.")
        await session.commit()
        await session.refresh(obj)
        logger.info("Hotel %s updated (fields: %s)", hotel_id, changed)
        return _row_to_dict(obj)

    async def cancel(
        self,
        session: AsyncSession,
        hotel_id: int,
        user_id: int | str,
    ) -> Dict:
        """Cancel a hotel booking by setting booked = 0."""
        obj = await self.get_by_id_or_raise(
            session, hotel_id,
            detail=f"Hotel with id={hotel_id} not found.",
        )
        obj.booked = 0
        await session.commit()
        await session.refresh(obj)
        logger.info("Hotel %s cancelled by user %s", hotel_id, user_id)
        return _row_to_dict(obj)


def _row_to_dict(row: object) -> Dict:
    return {c.key: getattr(row, c.key) for c in row.__table__.columns}


__all__ = ["HotelRepository"]
