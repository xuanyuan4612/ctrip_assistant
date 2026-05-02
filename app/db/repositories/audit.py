"""Audit event repository - structured audit logging."""
from __future__ import annotations

import logging
from datetime import datetime
from typing import Dict, Optional

from sqlalchemy import Integer, String, Text, DateTime, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Mapped, mapped_column

from app.db.models.business_base import BusinessBase
from app.db.repositories.base import AsyncBaseRepository

logger = logging.getLogger(__name__)


class AuditEventModel(BusinessBase):
    __tablename__ = "audit_events"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    user_id: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    action: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    entity: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    entity_id: Mapped[str] = mapped_column(String(100), nullable=False)
    detail: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, insert_default=func.now()
    )


class AuditRepository(AsyncBaseRepository[AuditEventModel]):
    """Async repository for audit event logging (write-only)."""

    def __init__(self) -> None:
        super().__init__(AuditEventModel)

    async def log(
        self,
        session: AsyncSession,
        user_id: str | int,
        action: str,
        entity: str,
        entity_id: str | int,
        detail: Optional[str] = None,
    ) -> Dict:
        """Record a structured audit event."""
        event = AuditEventModel(
            user_id=str(user_id),
            action=action,
            entity=entity,
            entity_id=str(entity_id),
            detail=detail,
        )
        session.add(event)
        await session.commit()
        await session.refresh(event)

        logger.info(
            "AUDIT|action=%s|entity=%s|entity_id=%s|user_id=%s|detail=%s",
            action, entity, entity_id, user_id, detail or "",
        )
        return {
            "id": event.id,
            "user_id": event.user_id,
            "action": event.action,
            "entity": event.entity,
            "entity_id": event.entity_id,
            "detail": event.detail,
            "created_at": event.created_at.isoformat() if event.created_at else None,
        }


__all__ = ["AuditRepository"]
