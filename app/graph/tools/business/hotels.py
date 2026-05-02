"""Hotel booking & management tools.

Mirrors legacy ``tools/hotels_tools.py`` with the following enhancements:

- ``ToolResult`` return type for write operations (``book_hotel``,
  ``update_hotel``, ``cancel_hotel``).
- ``ToolRuntime[UserContext, State]`` injection for identity / audit on writes.
- ``_audit()`` logging after every successful mutation.
- MySQL Repository placeholders (SQLite as temporary fallback).
- ``@tool`` docstrings preserved unchanged.
"""

from __future__ import annotations

import sqlite3  # TODO: replace with MySQL Repository (HotelRepository)
from datetime import date, datetime
from typing import Annotated, Optional, Union

from langchain_core.runnables import RunnableConfig
from langchain_core.tools import InjectedToolArg, tool

from app.graph.tools.types import TEMP_SQLITE_PATH, ToolResult, ToolRuntime, _audit
from app.graph.tools.knowledge.city_mapper import resolve_city

# ── MySQL Repository Placeholder ──────────────────────────────────────
# TODO: Uncomment when HotelRepository is implemented:
# from app.db.repositories.hotel_repository import HotelRepository
# repo = HotelRepository()


# ═══════════════════════════════════════════════════════════════════════
# Read Tools
# ═══════════════════════════════════════════════════════════════════════


@tool
def search_hotels(
    location: Optional[str] = None,
    name: Optional[str] = None,
) -> list[dict]:
    """根据位置、名称、价格层级、入住日期和退房日期搜索酒店。

    Args:
        location: 酒店的位置。默认为None。
        name: 酒店的名称。默认为None。

    Returns:
        包含匹配搜索条件的酒店信息的字典列表。
    """
    # TODO: replace with HotelRepository.search(location, name)
    conn = sqlite3.connect(TEMP_SQLITE_PATH)
    cursor = conn.cursor()

    location = resolve_city(location)
    query = "SELECT * FROM hotels WHERE 1=1"
    params = []

    if location:
        query += " AND location LIKE ?"
        params.append(f"%{location}%")
    if name:
        query += " AND name LIKE ?"
        params.append(f"%{name}%")

    print("查询酒店的SQL：" + query, "参数: ", params)
    cursor.execute(query, params)
    results = cursor.fetchall()
    print("查询酒店的结果: ", results)
    conn.close()

    return [
        dict(zip([column[0] for column in cursor.description], row)) for row in results
    ]


# ═══════════════════════════════════════════════════════════════════════
# Write Tools
# ═══════════════════════════════════════════════════════════════════════


@tool
def book_hotel(
    hotel_id: int,
    *,
    config: RunnableConfig,
    runtime: Annotated[ToolRuntime, InjectedToolArg],
) -> ToolResult:
    """通过ID预订酒店。

    Args:
        hotel_id: 要预订的酒店的ID。
        config: 配置信息。
        runtime: 运行时上下文，用于身份和审计。

    Returns:
        表明酒店是否成功预订的消息。
    """
    # TODO: replace with HotelRepository.book(hotel_id)
    conn = sqlite3.connect(TEMP_SQLITE_PATH)
    cursor = conn.cursor()

    try:
        cursor.execute("UPDATE hotels SET booked = 1 WHERE id = ?", (hotel_id,))
        conn.commit()

        if cursor.rowcount > 0:
            _audit(
                action="book",
                entity="hotel",
                entity_id=str(hotel_id),
                user_id=runtime.user_id,
                detail=f"Hotel {hotel_id} booked",
            )
            return ToolResult.ok(message=f"Hotel {hotel_id} 成功预定。")
        else:
            return ToolResult.fail("not_found", f"未找到ID为 {hotel_id} 的酒店。")
    except Exception as e:
        conn.rollback()
        return ToolResult.fail(str(type(e).__name__), str(e))
    finally:
        conn.close()


@tool
def update_hotel(
    hotel_id: int,
    checkin_date: Optional[Union[datetime, date]] = None,
    checkout_date: Optional[Union[datetime, date]] = None,
    *,
    config: RunnableConfig,
    runtime: Annotated[ToolRuntime, InjectedToolArg],
) -> ToolResult:
    """根据ID更新酒店预订的入住和退房日期。

    Args:
        hotel_id: 要更新的酒店预订的ID。
        checkin_date: 酒店的新入住日期。默认为None。
        checkout_date: 酒店的新退房日期。默认为None。
        config: 配置信息。
        runtime: 运行时上下文，用于身份和审计。

    Returns:
        表明酒店预订是否成功更新的消息。
    """
    # TODO: replace with HotelRepository.update(hotel_id, checkin, checkout)
    conn = sqlite3.connect(TEMP_SQLITE_PATH)
    cursor = conn.cursor()

    try:
        has_update = False
        if checkin_date:
            cursor.execute(
                "UPDATE hotels SET checkin_date = ? WHERE id = ?",
                (checkin_date, hotel_id),
            )
            has_update = True
        if checkout_date:
            cursor.execute(
                "UPDATE hotels SET checkout_date = ? WHERE id = ?",
                (checkout_date, hotel_id),
            )
            has_update = True

        if not has_update:
            return ToolResult.fail("no_changes", "没有提供需要更新的字段。")

        conn.commit()

        if cursor.rowcount == 0:
            return ToolResult.fail(
                "not_found", f"未找到ID为 {hotel_id} 的酒店。"
            )

        _audit(
            action="update",
            entity="hotel",
            entity_id=str(hotel_id),
            user_id=runtime.user_id,
            detail=f"checkin={checkin_date} checkout={checkout_date}",
        )

        return ToolResult.ok(message=f"Hotel {hotel_id} 成功更新。")
    except Exception as e:
        conn.rollback()
        return ToolResult.fail(str(type(e).__name__), str(e))
    finally:
        conn.close()


@tool
def cancel_hotel(
    hotel_id: int,
    *,
    config: RunnableConfig,
    runtime: Annotated[ToolRuntime, InjectedToolArg],
) -> ToolResult:
    """根据ID取消酒店预订。

    Args:
        hotel_id: 要取消的酒店预订的ID。
        config: 配置信息。
        runtime: 运行时上下文，用于身份和审计。

    Returns:
        表明酒店预订是否成功取消的消息。
    """
    # TODO: replace with HotelRepository.cancel(hotel_id)
    conn = sqlite3.connect(TEMP_SQLITE_PATH)
    cursor = conn.cursor()

    try:
        cursor.execute("UPDATE hotels SET booked = 0 WHERE id = ?", (hotel_id,))
        conn.commit()

        if cursor.rowcount > 0:
            _audit(
                action="cancel",
                entity="hotel",
                entity_id=str(hotel_id),
                user_id=runtime.user_id,
                detail=f"Hotel {hotel_id} cancelled",
            )
            return ToolResult.ok(message=f"Hotel {hotel_id} 成功取消。")
        else:
            return ToolResult.fail("not_found", f"未找到ID为 {hotel_id} 的酒店。")
    except Exception as e:
        conn.rollback()
        return ToolResult.fail(str(type(e).__name__), str(e))
    finally:
        conn.close()
