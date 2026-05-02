"""Shared types and utilities for the production tool layer.

Defines:
    - ``ToolResult`` — standardized return type for all tool operations
    - ``ToolRuntime`` — generic runtime context injected into tools
    - ``_audit()`` — structured audit-logging helper
    - ``TEMP_SQLITE_PATH`` — temporary DB path (removed after MySQL migration)
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, Generic, Optional, TypeVar

logger = logging.getLogger(__name__)

# ── Type Variables ────────────────────────────────────────────────────

T = TypeVar("T")
"""Type variable for ToolResult generic payload."""

UserContext = TypeVar("UserContext")
"""Type variable for the user identity carried by ToolRuntime."""

State = TypeVar("State")
"""Type variable for the LangGraph state carried by ToolRuntime."""


# ── ToolResult ────────────────────────────────────────────────────────


@dataclass
class ToolResult(Generic[T]):
    """Standardized result wrapper for all tool operations.

    Agents can pattern-match on the ``success`` flag instead of parsing
    ad-hoc string responses.  On success the ``data`` field carries the
    payload; on failure the ``error`` field carries a machine-readable
    error message.

    Example::

        return ToolResult.ok(data=flight_list, message="找到 5 个航班")
        return ToolResult.fail(error="ticket_not_found", message="机票不存在")
    """

    success: bool
    """Whether the tool operation completed successfully."""

    message: str = ""
    """Human-readable result message (shown to the end-user)."""

    data: Optional[T] = None
    """Structured payload returned on success (e.g. a list of records)."""

    error: Optional[str] = None
    """Machine-readable error code returned on failure."""

    metadata: Dict[str, Any] = field(default_factory=dict)
    """Extra key/value pairs for observability / debugging."""

    # ── Constructors ──────────────────────────────────────────────

    @classmethod
    def ok(
        cls,
        data: T = None,
        message: str = "操作成功",
        **metadata,
    ) -> ToolResult[T]:
        """Build a success result."""
        return cls(success=True, data=data, message=message, metadata=metadata)

    @classmethod
    def fail(
        cls,
        error: str,
        message: str = "操作失败",
        **metadata,
    ) -> ToolResult:
        """Build a failure result."""
        return cls(
            success=False,
            error=error,
            message=message,
            metadata=metadata,
        )

    # ── Helpers ───────────────────────────────────────────────────

    def __bool__(self) -> bool:
        """Allow ``if result: ...`` checks."""
        return self.success

    def __str__(self) -> str:
        if self.success:
            return self.message
        return f"错误: {self.error}"


# ── ToolRuntime ───────────────────────────────────────────────────────


@dataclass
class ToolRuntime(Generic[UserContext, State]):
    """Runtime context injected into every tool call.

    The LangGraph agent **layer** populates this before routing to tool
    nodes so that every tool has zero-cost access to:

    * ``user_context`` — the current user's identity (Pydantic model,
      dict, or plain str)
    * ``state`` — the full current ``State`` TypedDict of the graph
    * ``metadata`` — arbitrary key/value pairs (request-id, trace-id,
      tenant-id, ...)

    Write-oriented tools accept this as an ``Annotated[ToolRuntime,
    InjectedToolArg]`` parameter so that the LLM never sees it in the
    tool schema.
    """

    user_context: UserContext
    """The current user's identity object."""

    state: State
    """The current LangGraph state (TypedDict)."""

    metadata: Dict[str, Any] = field(default_factory=dict)
    """Observability / routing metadata set by the agent layer."""

    # ── Derived Properties ────────────────────────────────────────

    @property
    def user_id(self) -> str:
        """Return a stable string identifier for the current user."""
        if hasattr(self.user_context, "id"):
            return str(self.user_context.id)  # type: ignore[union-attr]
        return str(self.user_context)

    @property
    def passenger_id(self) -> Optional[str]:
        """Return the airline passenger ID if available."""
        if hasattr(self.user_context, "passenger_id"):
            return self.user_context.passenger_id  # type: ignore[union-attr]
        if isinstance(self.user_context, dict):
            return self.user_context.get("passenger_id")
        return None


# ── Audit Helper ──────────────────────────────────────────────────────


def _audit(
    action: str,
    entity: str,
    entity_id: str,
    user_id: str,
    detail: str | None = None,
) -> None:
    """Log a structured audit event for compliance / observability.

    Every write-oriented tool calls this after a successful mutation so
    that the logs contain an unbroken, queryable trail of all data
    changes.

    Args:
        action: Operation performed (``"book"``, ``"cancel"``,
            ``"update"``, ...).
        entity: Domain entity (``"flight_ticket"``, ``"hotel"``,
            ``"car_rental"``, ``"excursion"``).
        entity_id: Identifier of the affected record.
        user_id: Stable identifier of the user who performed the action.
        detail: Optional free-text description of the change.
    """
    logger.info(
        "AUDIT|action=%s|entity=%s|entity_id=%s|user_id=%s|detail=%s",
        action,
        entity,
        entity_id,
        user_id,
        detail or "",
    )


# ── Temporary SQLite Path (to be removed after MySQL migration) ───────

#: Absolute path to the legacy SQLite database used as temporary fallback
#: until MySQL Repository classes are implemented.
# TODO: Remove this constant and all ``sqlite3.connect(TEMP_SQLITE_PATH)``
#       calls once   app/db/repositories/   are operational.
TEMP_SQLITE_PATH = str(
    Path(__file__).resolve().parent.parent.parent.parent / "travel_new.sqlite"
)
