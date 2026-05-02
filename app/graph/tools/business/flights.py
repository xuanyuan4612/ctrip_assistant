"""Flight booking & management tools.

Mirrors legacy ``tools/flights_tools.py`` with the following enhancements:

- ``ToolResult`` return type for write operations (``update_ticket_to_new_flight``,
  ``cancel_ticket``).
- ``ToolRuntime[UserContext, State]`` injection for identity / audit on writes.
- ``_audit()`` logging after every successful mutation.
- MySQL Repository placeholders (SQLite as temporary fallback).
- ``@tool`` docstrings preserved unchanged.
"""

from __future__ import annotations

import sqlite3  # TODO: replace with MySQL Repository (FlightRepository)
from datetime import date, datetime
from pathlib import Path
from typing import Annotated, Dict, List, Optional

import pytz
from langchain_core.runnables import RunnableConfig
from langchain_core.tools import InjectedToolArg, tool

from app.graph.tools.types import TEMP_SQLITE_PATH, ToolResult, ToolRuntime, _audit

# ── MySQL Repository Placeholder ──────────────────────────────────────
# TODO: Uncomment when FlightRepository is implemented:
# from app.db.repositories.flight_repository import FlightRepository
# repo = FlightRepository()


# ═══════════════════════════════════════════════════════════════════════
# Read Tools
# ═══════════════════════════════════════════════════════════════════════


@tool
def fetch_user_flight_information(config: RunnableConfig) -> List[Dict]:
    """获取当前乘客的所有机票信息及其相关联的航班信息和座位分配情况。

    通过给定的乘客ID，从数据库中获取该乘客的所有机票信息。

    Returns:
        包含每张机票的详情、关联航班的信息及座位分配的字典列表。
    """
    configuration = config.get("configurable", {})
    passenger_id = configuration.get("passenger_id", None)
    if not passenger_id:
        raise ValueError("未配置乘客 ID。")

    # TODO: replace with FlightRepository.get_tickets_by_passenger(passenger_id)
    conn = sqlite3.connect(TEMP_SQLITE_PATH)
    cursor = conn.cursor()

    query = """
    SELECT 
        t.ticket_no, t.book_ref,
        f.flight_id, f.flight_no, f.departure_airport, f.arrival_airport,
        f.scheduled_departure, f.scheduled_arrival,
        bp.seat_no, tf.fare_conditions
    FROM 
        tickets t
        JOIN ticket_flights tf ON t.ticket_no = tf.ticket_no
        JOIN flights f ON tf.flight_id = f.flight_id
        JOIN boarding_passes bp ON bp.ticket_no = t.ticket_no AND bp.flight_id = f.flight_id
    WHERE 
        t.passenger_id = ?
    """
    cursor.execute(query, (passenger_id,))
    rows = cursor.fetchall()
    column_names = [column[0] for column in cursor.description]
    results = [dict(zip(column_names, row)) for row in rows]

    cursor.close()
    conn.close()
    return results


@tool
def search_flights(
    departure_airport: Optional[str] = None,
    arrival_airport: Optional[str] = None,
    start_time: Optional[date | datetime] = None,
    end_time: Optional[date | datetime] = None,
    limit: int = 20,
) -> List[Dict]:
    """根据指定的参数（如出发机场、到达机场、出发时间范围等）搜索航班。

    可以设置一个限制值来控制返回的结果数量。

    Args:
        departure_airport: 出发机场（可选）。
        arrival_airport: 到达机场（可选）。
        start_time: 出发时间范围的开始时间（可选）。
        end_time: 出发时间范围的结束时间（可选）。
        limit: 返回结果的最大数量，默认为20。

    Returns:
        匹配条件的航班信息列表。
    """
    # TODO: replace with FlightRepository.search(...)
    conn = sqlite3.connect(TEMP_SQLITE_PATH)
    cursor = conn.cursor()

    query = "SELECT * FROM flights WHERE 1 = 1"
    params: list = []

    if departure_airport:
        query += " AND departure_airport = ?"
        params.append(departure_airport)
    if arrival_airport:
        query += " AND arrival_airport = ?"
        params.append(arrival_airport)
    if start_time:
        query += " AND scheduled_departure >= ?"
        params.append(start_time)
    if end_time:
        query += " AND scheduled_departure <= ?"
        params.append(end_time)

    query += " LIMIT ?"
    params.append(limit)
    cursor.execute(query, params)
    rows = cursor.fetchall()
    column_names = [column[0] for column in cursor.description]
    results = [dict(zip(column_names, row)) for row in rows]

    cursor.close()
    conn.close()
    return results


# ═══════════════════════════════════════════════════════════════════════
# Write Tools
# ═══════════════════════════════════════════════════════════════════════


@tool
def update_ticket_to_new_flight(
    ticket_no: str,
    new_flight_id: int,
    *,
    config: RunnableConfig,
    runtime: Annotated[ToolRuntime, InjectedToolArg],
) -> ToolResult:
    """将用户的机票更新为新的有效航班。

    执行完整的验证链：
    1. 检查乘客ID
    2. 查询新航班详情
    3. 时间验证（起飞前至少3小时）
    4. 确认原机票存在性
    5. 验证乘客身份
    6. 更新机票信息

    Args:
        ticket_no: 要更新的机票编号。
        new_flight_id: 新的航班ID。
        config: 配置信息，包含乘客ID等必要参数。
        runtime: 运行时上下文，用于身份和审计。

    Returns:
        操作结果（ToolResult）。
    """
    configuration = config.get("configurable", {})
    passenger_id = configuration.get("passenger_id", None)
    if not passenger_id:
        return ToolResult.fail("missing_passenger_id", "未配置乘客 ID。")

    # TODO: replace with FlightRepository + MySQL transaction
    conn = sqlite3.connect(TEMP_SQLITE_PATH)
    cursor = conn.cursor()

    try:
        # 1. 查询新航班的信息
        cursor.execute(
            "SELECT departure_airport, arrival_airport, scheduled_departure "
            "FROM flights WHERE flight_id = ?",
            (new_flight_id,),
        )
        new_flight = cursor.fetchone()
        if not new_flight:
            return ToolResult.fail("invalid_flight_id", "提供的新的航班 ID 无效。")

        column_names = [column[0] for column in cursor.description]
        new_flight_dict = dict(zip(column_names, new_flight))

        # 2. 时间验证 — 必须起飞前至少3小时
        timezone = pytz.timezone("Etc/GMT-3")
        current_time = datetime.now(tz=timezone)
        departure_time = datetime.strptime(
            new_flight_dict["scheduled_departure"], "%Y-%m-%d %H:%M:%S.%f%z"
        )
        time_until = (departure_time - current_time).total_seconds()
        if time_until < (3 * 3600):
            return ToolResult.fail(
                "too_soon",
                f"不允许重新安排到距离当前时间少于 3 小时的航班。所选航班时间为 {departure_time}。",
            )

        # 3. 确认原机票存在性
        cursor.execute(
            "SELECT flight_id FROM ticket_flights WHERE ticket_no = ?",
            (ticket_no,),
        )
        if not cursor.fetchone():
            return ToolResult.fail("ticket_not_found", "未找到给定机票号码的现有机票。")

        # 4. 确认用户拥有此机票
        cursor.execute(
            "SELECT * FROM tickets WHERE ticket_no = ? AND passenger_id = ?",
            (ticket_no, passenger_id),
        )
        if not cursor.fetchone():
            return ToolResult.fail(
                "not_owner",
                f"当前登录的乘客 ID 为 {passenger_id}，不是机票 {ticket_no} 的拥有者。",
            )

        # 5. 执行更新
        cursor.execute(
            "UPDATE ticket_flights SET flight_id = ? WHERE ticket_no = ?",
            (new_flight_id, ticket_no),
        )
        conn.commit()

        _audit(
            action="update",
            entity="flight_ticket",
            entity_id=ticket_no,
            user_id=runtime.user_id,
            detail=f"Reassigned from to flight {new_flight_id}",
        )

        return ToolResult.ok(message="机票已成功更新为新的航班。")

    except Exception as e:
        conn.rollback()
        return ToolResult.fail(str(type(e).__name__), str(e))
    finally:
        cursor.close()
        conn.close()


@tool
def cancel_ticket(
    ticket_no: str,
    *,
    config: RunnableConfig,
    runtime: Annotated[ToolRuntime, InjectedToolArg],
) -> ToolResult:
    """取消用户的机票并将其从数据库中删除。

    执行完整的验证链：
    1. 检查乘客ID
    2. 查询机票存在性
    3. 验证乘客身份
    4. 删除机票信息

    Args:
        ticket_no: 要取消的机票编号。
        config: 配置信息，包含乘客ID。
        runtime: 运行时上下文，用于身份和审计。

    Returns:
        操作结果（ToolResult）。
    """
    configuration = config.get("configurable", {})
    passenger_id = configuration.get("passenger_id", None)
    if not passenger_id:
        return ToolResult.fail("missing_passenger_id", "未配置乘客 ID。")

    # TODO: replace with FlightRepository + MySQL transaction
    conn = sqlite3.connect(TEMP_SQLITE_PATH)
    cursor = conn.cursor()

    try:
        # 1. 查询机票存在性
        cursor.execute(
            "SELECT flight_id FROM ticket_flights WHERE ticket_no = ?",
            (ticket_no,),
        )
        if not cursor.fetchone():
            return ToolResult.fail("ticket_not_found", "未找到给定机票号码的现有机票。")

        # 2. 确认用户拥有此机票
        cursor.execute(
            "SELECT flight_id FROM tickets WHERE ticket_no = ? AND passenger_id = ?",
            (ticket_no, passenger_id),
        )
        if not cursor.fetchone():
            return ToolResult.fail(
                "not_owner",
                f"当前登录的乘客 ID 为 {passenger_id}，不是机票 {ticket_no} 的拥有者。",
            )

        # 3. 执行删除
        cursor.execute(
            "DELETE FROM ticket_flights WHERE ticket_no = ?",
            (ticket_no,),
        )
        conn.commit()

        _audit(
            action="cancel",
            entity="flight_ticket",
            entity_id=ticket_no,
            user_id=runtime.user_id,
            detail=f"Ticket cancelled by passenger {passenger_id}",
        )

        return ToolResult.ok(message="机票已成功取消。")

    except Exception as e:
        conn.rollback()
        return ToolResult.fail(str(type(e).__name__), str(e))
    finally:
        cursor.close()
        conn.close()
