"""City name resolution repository - port of tools/location_trans.py logic."""
from __future__ import annotations

import logging
from typing import Dict, Optional

from sqlalchemy import String, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Mapped, mapped_column

from app.db.models.business_base import BusinessBase
from app.db.repositories.base import AsyncBaseRepository

logger = logging.getLogger(__name__)


class CityMappingModel(BusinessBase):
    __tablename__ = "city_mappings"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    chinese_name: Mapped[Optional[str]] = mapped_column(String(50))
    english_name: Mapped[Optional[str]] = mapped_column(String(50))
    aliases: Mapped[Optional[str]] = mapped_column(String(200))
    iata_code: Mapped[Optional[str]] = mapped_column(String(5))


_FALLBACK_CITY_MAP: Dict[str, str] = {
    "Beijing": "Beijing",
    "Shanghai": "Shanghai",
    "Guangzhou": "Guangzhou",
    "Shenzhen": "Shenzhen",
    "Chengdu": "Chengdu",
    "Hangzhou": "Hangzhou",
    "Basel": "Basel",
    "Zurich": "Zurich",
}


def _is_chinese(text: str) -> bool:
    return all("\u4e00" <= char <= "\u9fff" for char in text)


class CityRepository(AsyncBaseRepository[CityMappingModel]):
    """Async repository for city name resolution.

    Resolution strategy:
    1. None/empty -> return as-is
    2. Non-CJK -> return unchanged (assumed already English)
    3. Exact match on chinese_name in city_mappings table
    4. LIKE match on aliases column
    5. Exact match on iata_code
    6. LIKE match on english_name (partial input)
    7. Static fallback dictionary
    8. Return input unchanged
    """

    def __init__(self) -> None:
        super().__init__(CityMappingModel)

    async def resolve(
        self,
        session: AsyncSession,
        name_or_code: Optional[str],
    ) -> Optional[str]:
        """Resolve a city name/code to its English form."""
        if not name_or_code:
            return name_or_code
        if not _is_chinese(name_or_code):
            return name_or_code

        # Step 1: exact match on chinese_name
        stmt = select(CityMappingModel).where(
            CityMappingModel.chinese_name == name_or_code
        )
        result = await session.execute(stmt)
        row = result.scalar_one_or_none()
        if row and row.english_name:
            logger.debug("City resolved via chinese_name: %s -> %s", name_or_code, row.english_name)
            return row.english_name

        # Step 2: LIKE match on aliases
        stmt = select(CityMappingModel).where(
            CityMappingModel.aliases.like(f"%{name_or_code}%")
        )
        result = await session.execute(stmt)
        row = result.scalar_one_or_none()
        if row and row.english_name:
            logger.debug("City resolved via aliases: %s -> %s", name_or_code, row.english_name)
            return row.english_name

        # Step 3: exact match on iata_code
        stmt = select(CityMappingModel).where(
            CityMappingModel.iata_code == name_or_code.upper()
        )
        result = await session.execute(stmt)
        row = result.scalar_one_or_none()
        if row and row.english_name:
            logger.debug("City resolved via iata_code: %s -> %s", name_or_code, row.english_name)
            return row.english_name

        # Step 4: LIKE match on english_name
        stmt = select(CityMappingModel).where(
            CityMappingModel.english_name.like(f"%{name_or_code}%")
        )
        result = await session.execute(stmt)
        row = result.scalar_one_or_none()
        if row and row.english_name:
            logger.debug("City resolved via english_name LIKE: %s -> %s", name_or_code, row.english_name)
            return row.english_name

        # Step 5: fallback dict
        fallback = _FALLBACK_CITY_MAP.get(name_or_code)
        if fallback:
            logger.debug("City resolved via fallback dict: %s -> %s", name_or_code, fallback)
            return fallback

        logger.warning("Unrecognised city name: %s - returning as-is", name_or_code)
        return name_or_code


__all__ = ["CityRepository"]
