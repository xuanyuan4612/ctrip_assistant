"""Excursion / trip recommendation repository."""
from __future__ import annotations

import logging
from typing import Dict, List, Optional

from sqlalchemy import String, select, Text, or_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Mapped, mapped_column

from app.core.exceptions import NotFoundError
from app.db.models.business_base import BusinessBase
from app.db.repositories.base import AsyncBaseRepository

logger = logging.getLogger(__name__)


class TripRecommendationModel(BusinessBase):
    __tablename__ = "trip_recommendations"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[Optional[str]] = mapped_column(String(100))
    location: Mapped[Optional[str]] = mapped_column(String(100))
    keywords: Mapped[Optional[str]] = mapped_column(Text)
    details: Mapped[Optional[str]] = mapped_column(Text)
    booked: Mapped[Optional[int]] = mapped_column(default=0)


class ExcursionRepository(AsyncBaseRepository[TripRecommendationModel]):
    """Async repository for excursion / trip recommendation management."""

    def __init__(self) -> None:
        super().__init__(TripRecommendationModel)

    async def search(
        self,
        session: AsyncSession,
        location: Optional[str] = None,
        name: Optional[str] = None,
        keywords: Optional[str] = None,
    ) -> List[Dict]:
        """Search trip recommendations by location, name, and keywords."""
        stmt = select(TripRecommendationModel).where(1 == 1)
        if location:
            stmt = stmt.where(TripRecommendationModel.location.like(f"%{location}%"))
        if name:
            stmt = stmt.where(TripRecommendationModel.name.like(f"%{name}%"))
        if keywords:
            kw_list = [k.strip() for k in keywords.split(",") if k.strip()]
            if kw_list:
                conditions = [
                    TripRecommendationModel.keywords.like(f"%{kw}%")
                    for kw in kw_list
                ]
                stmt = stmt.where(or_(*conditions))
        result = await session.execute(stmt)
        return [_row_to_dict(r) for r in result.scalars().all()]

    async def book(
        self,
        session: AsyncSession,
        recommendation_id: int,
        user_id: int | str,
    ) -> Dict:
        """Book a trip recommendation by setting booked = 1."""
        obj = await self.get_by_id_or_raise(
            session, recommendation_id,
            detail=f"Trip recommendation with id={recommendation_id} not found.",
        )
        obj.booked = 1
        await session.commit()
        await session.refresh(obj)
        logger.info("Excursion %s booked by user %s", recommendation_id, user_id)
        return _row_to_dict(obj)

    async def update(
        self,
        session: AsyncSession,
        recommendation_id: int,
        details: str,
    ) -> Dict:
        """Update the details field of a trip recommendation."""
        obj = await self.get_by_id_or_raise(
            session, recommendation_id,
            detail=f"Trip recommendation with id={recommendation_id} not found.",
        )
        obj.details = details
        await session.commit()
        await session.refresh(obj)
        logger.info("Excursion %s details updated", recommendation_id)
        return _row_to_dict(obj)

    async def cancel(
        self,
        session: AsyncSession,
        recommendation_id: int,
        user_id: int | str,
    ) -> Dict:
        """Cancel a trip recommendation by setting booked = 0."""
        obj = await self.get_by_id_or_raise(
            session, recommendation_id,
            detail=f"Trip recommendation with id={recommendation_id} not found.",
        )
        obj.booked = 0
        await session.commit()
        await session.refresh(obj)
        logger.info("Excursion %s cancelled by user %s", recommendation_id, user_id)
        return _row_to_dict(obj)


def _row_to_dict(row: object) -> Dict:
    return {c.key: getattr(row, c.key) for c in row.__table__.columns}


__all__ = ["ExcursionRepository"]
