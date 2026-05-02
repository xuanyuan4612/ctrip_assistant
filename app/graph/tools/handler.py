"""ToolNode with fallback handling + event printing.

This module mirrors the legacy ``tools/tools_handler.py`` and provides
the same two public functions that the existing graph builders depend on:

* ``create_tool_node_with_fallback(tools)`` — wraps ``ToolNode`` with
  automatic error recovery.
* ``_print_event(event, _printed)`` — pretty-prints graph events for
  debugging / REPL use.

It also exports ``handle_tool_error``, the fallback callback, for
any caller that wants to customise error handling.
"""

from langchain_core.messages import ToolMessage
from langchain_core.runnables import RunnableLambda
from langgraph.prebuilt import ToolNode


def handle_tool_error(state: dict) -> dict:
    """Handle errors that occur during tool execution.

    Called by the fallback mechanism when a tool raises an exception.

    Args:
        state: The current graph state dictionary, containing ``"error"``
            and ``"messages"`` keys.

    Returns:
        A dict with a ``"messages"`` key containing ``ToolMessage``
        instances that report the error for each failed tool call.
    """
    error = state.get("error")
    tool_calls = state["messages"][-1].tool_calls
    return {
        "messages": [
            ToolMessage(
                content=f"错误: {repr(error)}\n请修正您的错误。",
                tool_call_id=tc["id"],
            )
            for tc in tool_calls
        ]
    }


def create_tool_node_with_fallback(tools: list) -> ToolNode:
    """Create a ``ToolNode`` with automatic fallback on failure.

    When a tool raises an exception the fallback catches it and returns
    a user-friendly error message instead of crashing the graph.

    Args:
        tools: List of ``@tool``-decorated functions or ``BaseTool``
            instances to include in the node.

    Returns:
        A ``ToolNode`` wrapped with ``.with_fallbacks(...)``.
    """
    return ToolNode(tools).with_fallbacks(
        [RunnableLambda(handle_tool_error)],
        exception_key="error",
    )


def _print_event(event: dict, _printed: set, max_length: int = 1500) -> None:
    """Pretty-print a graph event for debugging / REPL sessions.

    Shows the current dialog state and the content of the last message,
    truncating long messages to keep the output readable.

    Args:
        event: The event dictionary emitted by the graph, typically
            containing ``"dialog_state"`` and ``"messages"`` keys.
        _printed: Mutable set of message IDs that have already been
            printed (used to avoid duplicates across multiple steps).
        max_length: Maximum character length before truncation.
    """
    current_state = event.get("dialog_state")
    if current_state:
        print("当前处于: ", current_state[-1])

    message = event.get("messages")
    if message:
        if isinstance(message, list):
            message = message[-1]
        if message.id not in _printed:
            msg_repr = message.pretty_repr(html=True)
            if len(msg_repr) > max_length:
                msg_repr = msg_repr[:max_length] + " ... （已截断）"
            print(msg_repr)
            _printed.add(message.id)


__all__ = [
    "handle_tool_error",
    "create_tool_node_with_fallback",
    "_print_event",
]
