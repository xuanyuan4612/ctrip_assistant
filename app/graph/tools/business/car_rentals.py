"""Car rental booking & management tools.

Mirrors legacy ``tools/car_tools.py`` with the following enhancements:

- ``ToolResult`` return type for write operations (``book_car_rental``,
  ``update_car_rental``, ``cancel_car_rental``).
- ``ToolRuntime[UserContext, State]`` injection for identity / audit on writes.
- ``_audit()`` logging after every successful mutation.
- MySQL Repository placeholders (SQLite as temporary fallback).
- ``@tool`` docstrings preserved unchanged.
"""

from __future__ import annotations

import sqlite3  # TODO: replace with MySQL Repository (CarRentalRepository)
from datetime import date, datetime
from typing import Annotated, Optional, Union

from langchain_core.runnables import RunnableConfig
from langchain_core.tools import InjectedToolArg, tool

from app.graph.tools.types import TEMP_SQLITE_PATH, ToolResult, ToolRuntime, _audit
from app.graph.tools.knowledge.city_mapper import resolve_city

# ── MySQL Repository Placeholder ──────────────────────────────────────
# TODO: Uncomment when CarRentalRepository is implemented:
# from app.db.repositories.car_rental_repository import CarRentalRepository
# repo = CarRentalRepository()


# ═══════════════════════════════════════════════════════════════════════
# Read Tools
# ═══════════════════════════════════════════════════════════════════════


@tool
def search_car_rentals(
    location: Optional[str] = None,
    name: Optional[str] = None,
) -> list[dict]:
    """根据位置、名称、价格层级、开始日期和结束日期搜索汽车租赁信息。

    Args:
        location: 汽车租赁的位置。默认为None。
        name: 汽车租赁公司的名称。默认为None。

    Returns:
        包含匹配搜索条件的汽车租赁信息的字典列表。
    """
    # TODO: replace with CarRentalRepository.search(location, name)
    conn = sqlite3.connect(TEMP_SQLITE_PATH)
    cursor = conn.cursor()

    location = resolve_city(location)
    query = "SELECT * FROM car_rentals WHERE 1=1"
    params = []

    if location:
        query += " AND location LIKE ?"
        params.append(f"%{location}%")
    if name:
        query += " AND name LIKE ?"
        params.append(f"%{name}%")

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
def book_car_rental(
    rental_id: int,
    *,
    config: RunnableConfig,
    runtime: Annotated[ToolRuntime, InjectedToolArg],
) -> ToolResult:
    """通过ID预订汽车租赁服务。

    Args:
        rental_id: 要预订的汽车租赁服务的ID。
        config: 配置信息。
        runtime: 运行时上下文，用于身份和审计。

    Returns:
        表明汽车租赁是否成功预订的消息。
    """
    # TODO: replace with CarRentalRepository.book(rental_id)
    conn = sqlite3.connect(TEMP_SQLITE_PATH)
    cursor = conn.cursor()

    try:
        cursor.execute(
            "UPDATE car_rentals SET booked = 1 WHERE id = ?", (rental_id,)
        )
        conn.commit()

        if cursor.rowcount > 0:
            _audit(
                action="book",
                entity="car_rental",
                entity_id=str(rental_id),
                user_id=runtime.user_id,
                detail=f"Car rental {rental_id} booked",
            )
            return ToolResult.ok(message=f"汽车租赁 {rental_id} 成功预订。")
        else:
            return ToolResult.fail(
                "not_found", f"未找到ID为 {rental_id} 的汽车租赁服务。"
            )
    except Exception as e:
        conn.rollback()
        return ToolResult.fail(str(type(e).__name__), str(e))
    finally:
        conn.close()


@tool
def update_car_rental(
    rental_id: int,
    start_date: Optional[Union[datetime, date]] = None,
    end_date: Optional[Union[datetime, date]] = None,
    *,
    config: RunnableConfig,
    runtime: Annotated[ToolRuntime, InjectedToolArg],
) -> ToolResult:
    """根据ID更新汽车租赁的开始和结束日期。

    Args:
        rental_id: 要更新的汽车租赁服务的ID。
        start_date: 汽车租赁的新开始日期。默认为None。
        end_date: 汽车租赁的新结束日期。默认为None。
        config: 配置信息。
        runtime: 运行时上下文，用于身份和审计。

    Returns:
        表明汽车租赁是否成功更新的消息。
    """
    # TODO: replace with CarRentalRepository.update(rental_id, start, end)
    conn = sqlite3.connect(TEMP_SQLITE_PATH)
    cursor = conn.cursor()

    try:
        has_update = False
        if start_date:
            cursor.execute(
                "UPDATE car_rentals SET start_date = ? WHERE id = ?",
                (start_date, rental_id),
            )
            has_update = True
        if end_date:
            cursor.execute(
                "UPDATE car_rentals SET end_date = ? WHERE id = ?",
                (end_date, rental_id),
            )
            has_update = True

        if not has_update:
            return ToolResult.fail("no_changes", "没有提供需要更新的字段。")

        conn.commit()

        if cursor.rowcount == 0:
            return ToolResult.fail(
                "not_found", f"未找到ID为 {rental_id} 的汽车租赁服务。"
            )

        _audit(
            action="update",
            entity="car_rental",
            entity_id=str(rental_id),
            user_id=runtime.user_id,
            detail=f"start={start_date} end={end_date}",
        )

        return ToolResult.ok(message=f"汽车租赁 {rental_id} 成功更新。")
    except Exception as e:
        conn.rollback()
        return ToolResult.fail(str(type(e).__name__), str(e))
    finally:
        conn.close()


@tool
def cancel_car_rental(
    rental_id: int,
    *,
    config: RunnableConfig,
    runtime: Annotated[ToolRuntime, InjectedToolArg],
) -> ToolResult:
    """根据ID取消汽车租赁服务。

    Args:
        rental_id: 要取消的汽车租赁服务的ID。
        config: 配置信息。
        runtime: 运行时上下文，用于身份和审计。

    Returns:
        表明汽车租赁是否成功取消的消息。
    """
    # TODO: replace with CarRentalRepository.cancel(rental_id)
    conn = sqlite3.connect(TEMP_SQLITE_PATH)
    cursor = conn.cursor()

    try:
        cursor.execute(
            "UPDATE car_rentals SET booked = 0 WHERE id = ?", (rental_id,)
        )
        conn.commit()

        if cursor.rowcount > 0:
            _audit(
                action="cancel",
                entity="car_rental",
                entity_id=str(rental_id),
                user_id=runtime.user_id,
                detail=f"Car rental {rental_id} cancelled",
            )
            return ToolResult.ok(message=f"汽车租赁 {rental_id} 成功取消。")
        else:
            return ToolResult.fail(
                "not_found", f"未找到ID为 {rental_id} 的汽车租赁服务。"
            )
    except Exception as e:
        conn.rollback()
        return ToolResult.fail(str(type(e).__name__), str(e))
    finally:
        conn.close()
