"""Async base repository with generic CRUD operations."""
from __future__ import annotations

from typing import Generic, List, Optional, Type, TypeVar

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import NotFoundError

ModelType = TypeVar("ModelType")


class AsyncBaseRepository(Generic[ModelType]):
    """Generic async repository providing standard CRUD operations.

    All public methods accept an AsyncSession as the first argument.
    """

    def __init__(self, model: Type[ModelType]) -> None:
        if model is None:
            raise ValueError("model class is required")
        self.model = model

    async def get_by_id(
        self, session: AsyncSession, pk: int,
    ) -> Optional[ModelType]:
        """Return one record by primary key, or None."""
        return await session.get(self.model, pk)

    async def get_by_id_or_raise(
        self, session: AsyncSession, pk: int,
        detail: str | None = None,
    ) -> ModelType:
        """Like get_by_id but raises NotFoundError on miss."""
        obj = await self.get_by_id(session, pk)
        if obj is None:
            raise NotFoundError(
                detail or f"{self.model.__name__} with id={pk} not found"
            )
        return obj

    async def get_all(
        self, session: AsyncSession,
        skip: int = 0, limit: int = 100,
    ) -> List[ModelType]:
        """Return a paginated list of all records."""
        stmt = select(self.model).offset(skip).limit(limit)
        result = await session.execute(stmt)
        return list(result.scalars().all())

    async def create(
        self, session: AsyncSession, **kwargs: object,
    ) -> ModelType:
        """Create and return a new record from keyword arguments."""
        obj = self.model(**kwargs)
        session.add(obj)
        await session.commit()
        await session.refresh(obj)
        return obj

    async def update(
        self, session: AsyncSession, pk: int, **kwargs: object,
    ) -> ModelType:
        """Update by primary key. Raises NotFoundError on miss."""
        obj = await self.get_by_id_or_raise(session, pk)
        for key, value in kwargs.items():
            if hasattr(obj, key):
                setattr(obj, key, value)
        await session.commit()
        await session.refresh(obj)
        return obj

    async def delete(self, session: AsyncSession, pk: int) -> None:
        """Delete by primary key. Raises NotFoundError on miss."""
        obj = await self.get_by_id_or_raise(session, pk)
        await session.delete(obj)
        await session.commit()

    async def count(self, session: AsyncSession) -> int:
        """Return the total number of records."""
        stmt = select(func.count()).select_from(self.model)
        result = await session.execute(stmt)
        return result.scalar_one()


__all__ = ["AsyncBaseRepository"]
