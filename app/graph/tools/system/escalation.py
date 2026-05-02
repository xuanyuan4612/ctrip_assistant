"""CompleteOrEscalate — handoff / escalation tool for sub-agents.

Every specialised sub-agent (flight, hotel, car-rental, excursion)
binds this tool so it can signal completion or escalate back to the
primary assistant.

This mirrors the legacy ``graph_chat/base_data_model.py`` →
``CompleteOrEscalate`` class, but implemented as a proper LangChain
``@tool`` so it integrates cleanly into the production tool layer.
"""

from __future__ import annotations

from typing import Annotated

from langchain_core.tools import InjectedToolArg, tool

from app.graph.tools.types import ToolResult, ToolRuntime


@tool
def complete_or_escalate(
    cancel: bool = True,
    reason: str = "",
    *,
    runtime: Annotated[ToolRuntime, InjectedToolArg],
) -> ToolResult:
    """将当前子任务标记为已完成和／或将对话的控制权升级到主助理。

    当专门助理（航班、酒店、租车、游览）完成其任务,或遇到自身
    工具无法处理的情况时,调用此工具将控制权交还给主助理。

    Args:
        cancel: 如果为 ``True``,表示取消/结束当前任务；
                如果为 ``False``,表示任务已完成但需要主助理跟进。
        reason: 取消或升级的原因说明,主助理会据此决定下一步操作。

    Returns:
        ToolResult — 包含处理结果的信息。
    """
    action = "cancel" if cancel else "complete"
    detail = reason or "未提供原因"

    if runtime:
        _log_escalation(action, detail, runtime)

    if cancel:
        return ToolResult.ok(
            message=f"任务已取消。原因: {detail}",
            metadata={"escalation": action, "reason": detail},
        )

    return ToolResult.ok(
        message=f"任务已完成,正在回到主助理。原因: {detail}",
        metadata={"escalation": action, "reason": detail},
    )


def _log_escalation(action: str, reason: str, runtime: ToolRuntime) -> None:
    """Log an escalation event for observability."""
    import logging

    logger = logging.getLogger(__name__)
    logger.info(
        "ESCALATION|action=%s|user=%s|reason=%s",
        action,
        runtime.user_id,
        reason,
    )


__all__ = ["complete_or_escalate"]
