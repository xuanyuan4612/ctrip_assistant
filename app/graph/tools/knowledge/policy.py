"""RAG policy lookup — delegates to the vector-search engine.

This module provides the ``lookup_policy`` tool that agents use to
retrieve airline/travel policies from the FAQ knowledge base.

Architecture
------------
This is a **shim** that currently imports the fully-built RAG engine
from the legacy ``tools.retriever_engine`` module.  In the future the
import will switch to the new infrastructure layer:

    ``app.infrastructure.vector.retriever → get_retriever_tool()``

Once ``app/infrastructure/vector/`` is populated, change the import
below and delete this comment.
"""

from __future__ import annotations

import logging
from typing import Annotated

from langchain_core.tools import InjectedToolArg, tool

from app.graph.tools.types import ToolResult, ToolRuntime

logger = logging.getLogger(__name__)

# ── Import Target ─────────────────────────────────────────────────────
# Currently delegates to the legacy RAG engine.
# TODO: Replace with:
#   from app.infrastructure.vector.retriever import get_retriever_tool
from tools.retriever_engine import get_retriever_tool  # type: ignore[import-untyped]

# Build the retriever tool once at module load time.
# The ``auto_sync=True`` flag triggers first-time index synchronisation
# (reads the FAQ Markdown file, chunks it, and indexes into Qdrant).
_lookup_policy_impl = get_retriever_tool(auto_sync=True)


# ── Public Tool ───────────────────────────────────────────────────────


@tool
def lookup_policy(
    query: str,
    *,
    runtime: Annotated[ToolRuntime, InjectedToolArg] = None,
) -> str:
    """查询航空公司和旅行相关政策。

    在回答用户关于预订、取消、改签、支付、发票、行李等问题之前，
    使用此函数检索相关上下文。返回来自 FAQ 知识库的相关政策段落。

    Args:
        query: 用户的政策相关问题（如"怎么退票？"、"行李限额是多少？"）。
        runtime: （自动注入）运行时上下文，用于审计跟踪。

    Returns:
        格式化后的相关政策文本，包含来源章节标识。
    """
    if runtime:
        logger.debug(
            "Policy lookup by user=%s query=%s",
            runtime.user_id,
            query,
        )

    result = _lookup_policy_impl(query)

    if not result or result == "未找到相关政策信息。":
        logger.info("Policy lookup returned no results for query=%s", query)
        return "未找到相关政策信息。"

    return result


# Re-export the wrapped result for backward compatibility with any
# caller that still imports ``lookup_policy`` directly.
__all__ = ["lookup_policy"]
