"""Excursion / trip recommendation tools.

Mirrors legacy ``tools/trip_tools.py`` with the following enhancements:

- ``ToolResult`` return type for write operations (``book_excursion``,
  ``update_excursion``, ``cancel_excursion``).
- ``ToolRuntime[UserContext, State]`` injection for identity / audit on writes.
- ``_audit()`` logging after every successful mutation.
- MySQL Repository placeholders (SQLite as temporary fallback).
- ``@tool`` docstrings preserved unchanged.
"""

from __future__ import annotations

import sqlite3  # TODO: replace with MySQL Repository (ExcursionRepository)
from typing import Annotated, List, Optional

from langchain_core.runnables import RunnableConfig
from langchain_core.tools import InjectedToolArg, tool

from app.graph.tools.types import TEMP_SQLITE_PATH, ToolResult, ToolRuntime, _audit
from app.graph.tools.knowledge.city_mapper import resolve_city

# ── MySQL Repository Placeholder ──────────────────────────────────────
# TODO: Uncomment when ExcursionRepository is implemented:
# from app.db.repositories.excursion_repository import ExcursionRepository
# repo = ExcursionRepository()


# ═══════════════════════════════════════════════════════════════════════
# Read Tools
# ═══════════════════════════════════════════════════════════════════════


@tool
def search_trip_recommendations(
    location: Optional[str] = None,
    name: Optional[str] = None,
    keywords: Optional[str] = None,
) -> List[dict]:
    """根据位置、名称和关键词搜索旅行推荐。

    Args:
        location: 旅行推荐的位置。默认为None。
        name: 旅行推荐的名称。默认为None。
        keywords: 关联到旅行推荐的关键词。默认为None。

    Returns:
        包含匹配搜索条件的旅行推荐字典列表。
    """
    # TODO: replace with ExcursionRepository.search(location, name, keywords)
    conn = sqlite3.connect(TEMP_SQLITE_PATH)
    cursor = conn.cursor()

    location = resolve_city(location)
    query = "SELECT * FROM trip_recommendations WHERE 1=1"
    params = []

    if location:
        query += " AND location LIKE ?"
        params.append(f"%{location}%")
    if name:
        query += " AND name LIKE ?"
        params.append(f"%{name}%")
    if keywords:
        keyword_list = keywords.split(",")
        keyword_conditions = " OR ".join(
            ["keywords LIKE ?" for _ in keyword_list]
        )
        query += f" AND ({keyword_conditions})"
        params.extend([f"%{keyword.strip()}%" for keyword in keyword_list])

    cursor.execute(query, params)
    results = cursor.fetchall()
    conn.close()

    return [
        dict(zip([column[0] for column in cursor.description], row)) for row in results
    ]


# ═══════════════════════════════════════════════════════════════════════
# Write Tools
# ═══════════════════════════════════════════════════════════════════════


@tool
def book_excursion(
    recommendation_id: int,
    *,
    config: RunnableConfig,
    runtime: Annotated[ToolRuntime, InjectedToolArg],
) -> ToolResult:
    """通过推荐ID预订一次旅行项目。

    Args:
        recommendation_id: 要预订的旅行推荐的ID。
        config: 配置信息。
        runtime: 运行时上下文，用于身份和审计。

    Returns:
        表明旅行推荐是否成功预订的消息。
    """
    # TODO: replace with ExcursionRepository.book(recommendation_id)
    conn = sqlite3.connect(TEMP_SQLITE_PATH)
    cursor = conn.cursor()

    try:
        cursor.execute(
            "UPDATE trip_recommendations SET booked = 1 WHERE id = ?",
            (recommendation_id,),
        )
        conn.commit()

        if cursor.rowcount > 0:
            _audit(
                action="book",
                entity="excursion",
                entity_id=str(recommendation_id),
                user_id=runtime.user_id,
                detail=f"Excursion {recommendation_id} booked",
            )
            return ToolResult.ok(message=f"旅行推荐 {recommendation_id} 成功预定。")
        else:
            return ToolResult.fail(
                "not_found",
                f"未找到与 ID 相关的旅行推荐信息。 {recommendation_id}.",
            )
    except Exception as e:
        conn.rollback()
        return ToolResult.fail(str(type(e).__name__), str(e))
    finally:
        conn.close()


@tool
def update_excursion(
    recommendation_id: int,
    details: str,
    *,
    config: RunnableConfig,
    runtime: Annotated[ToolRuntime, InjectedToolArg],
) -> ToolResult:
    """根据ID更新旅行推荐的详细信息。

    Args:
        recommendation_id: 要更新的旅行推荐的ID。
        details: 旅行推荐的新详细信息。
        config: 配置信息。
        runtime: 运行时上下文，用于身份和审计。

    Returns:
        表明旅行推荐是否成功更新的消息。
    """
    # TODO: replace with ExcursionRepository.update(recommendation_id, details)
    conn = sqlite3.connect(TEMP_SQLITE_PATH)
    cursor = conn.cursor()

    try:
        cursor.execute(
            "UPDATE trip_recommendations SET details = ? WHERE id = ?",
            (details, recommendation_id),
        )
        conn.commit()

        _audit(
            action="update",
            entity="excursion",
            entity_id=str(recommendation_id),
            user_id=runtime.user_id,
            detail=f"Details updated for excursion {recommendation_id}",
        )

        return ToolResult.ok(message=f"旅行推荐 {recommendation_id} 成功更新。")
    except Exception as e:
        conn.rollback()
        return ToolResult.fail(str(type(e).__name__), str(e))
    finally:
        conn.close()


@tool
def cancel_excursion(
    recommendation_id: int,
    *,
    config: RunnableConfig,
    runtime: Annotated[ToolRuntime, InjectedToolArg],
) -> ToolResult:
    """根据ID取消旅行推荐。

    Args:
        recommendation_id: 要取消的旅行推荐的ID。
        config: 配置信息。
        runtime: 运行时上下文，用于身份和审计。

    Returns:
        表明旅行推荐是否成功取消的消息。
    """
    # TODO: replace with ExcursionRepository.cancel(recommendation_id)
    conn = sqlite3.connect(TEMP_SQLITE_PATH)
    cursor = conn.cursor()

    try:
        cursor.execute(
            "UPDATE trip_recommendations SET booked = 0 WHERE id = ?",
            (recommendation_id,),
        )
        conn.commit()

        if cursor.rowcount > 0:
            _audit(
                action="cancel",
                entity="excursion",
                entity_id=str(recommendation_id),
                user_id=runtime.user_id,
                detail=f"Excursion {recommendation_id} cancelled",
            )
            return ToolResult.ok(message=f"旅行推荐 {recommendation_id} 成功取消。")
        else:
            return ToolResult.fail(
                "not_found", f"未找到ID为 {recommendation_id} 的旅行推荐。"
            )
    except Exception as e:
        conn.rollback()
        return ToolResult.fail(str(type(e).__name__), str(e))
    finally:
        conn.close()
