"""RequestClarification — ask the user for missing information.

When an agent determines that it cannot proceed because required
parameters are missing (e.g. no departure city, no dates, ambiguous
location), it calls ``request_clarification`` to ask the user for the
missing details instead of guessing or failing silently.
"""

from __future__ import annotations

from typing import Annotated, List, Optional

from langchain_core.tools import InjectedToolArg, tool

from app.graph.tools.types import ToolResult, ToolRuntime


@tool
def request_clarification(
    question: str,
    *,
    options: Optional[List[str]] = None,
    runtime: Annotated[ToolRuntime, InjectedToolArg],
) -> ToolResult:
    """向用户请求澄清或补充缺失的信息。

    当工具无法继续执行时（如缺少必要参数、用户输入模糊）,调用此
    函数询问用户提供更多细节。

    请提供一个清晰、具体的问题,并可选地提供选项列表以引导用户。

    Args:
        question: 向用户提出的问题,应该具体且容易理解
                  （如"请问您的出发城市是哪个？"）。
        options: 可选的选项列表,用于限制用户的回答范围
                 （如 ["北京", "上海", "广州"]）。

    Returns:
        ToolResult — 包含询问状态的信息。
    """
    if runtime:
        _log_clarification(question, options, runtime)

    if options:
        formatted_options = ", ".join(options)
        full_message = f"{question}\n可选选项: {formatted_options}"
    else:
        full_message = question

    return ToolResult.ok(
        message=full_message,
        metadata={"clarification": True, "question": question, "options": options},
    )


def _log_clarification(
    question: str, options: Optional[List[str]], runtime: ToolRuntime
) -> None:
    """Log a clarification request for observability."""
    import logging

    logger = logging.getLogger(__name__)
    logger.info(
        "CLARIFICATION|user=%s|question=%s|options=%s",
        runtime.user_id,
        question,
        options,
    )


__all__ = ["request_clarification"]
