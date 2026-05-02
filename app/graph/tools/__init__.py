"""Production tool layer for LangGraph agents.

This package provides the tool implementations that LangGraph agents
bind to.  Every tool follows a consistent pattern:

- ``@tool`` decorator with full docstring (preserved from legacy)
- ``ToolResult`` return type for write operations
- ``ToolRuntime[UserContext, State]`` injection for identity / audit
- ``_audit()`` logging for compliance observability
- MySQL Repository placeholders (SQLite as temporary fallback)
"""

from app.graph.tools.types import ToolResult, ToolRuntime, _audit
from app.graph.tools.handler import (
    _print_event,
    create_tool_node_with_fallback,
    handle_tool_error,
)

__all__ = [
    # types
    "ToolResult",
    "ToolRuntime",
    "_audit",
    # handler
    "create_tool_node_with_fallback",
    "handle_tool_error",
    "_print_event",
]
