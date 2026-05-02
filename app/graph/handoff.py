"""
handoff.py -- Handoff Protocol

Provides the entry-node factory, dialog-state stack management,
and a direct peer-to-peer (P2P) handoff function for agent-to-agent
control transfer.
"""

from __future__ import annotations
import logging
from typing import Callable
from langchain_core.messages import ToolMessage

logger = logging.getLogger(__name__)


def create_entry_node(display_name: str, dialog_state_key: str) -> Callable:
    """Create an entry-node callable that sets up a sub-agent context."""
    def entry_node(state: dict) -> dict:
        tool_call_id = state["messages"][-1].tool_calls[0]["id"]
        return {
            "messages": [
                ToolMessage(
                    content=(
                        f"Now serving as {display_name}. Review the above conversation. "
                        f"The user's intent is not yet fulfilled. Use the provided tools to assist. "
                        f"Remember you are {display_name} and the task is not complete "
                        f"until the appropriate tools have been called successfully. "
                        f"If the user changes their mind or needs help with another task, "
                        f"call CompleteOrEscalate to hand back to the main assistant. "
                        f"Do not mention who you are -- act as the agent proxy."
                    ),
                    tool_call_id=tool_call_id,
                )
            ],
            "dialog_state": dialog_state_key,
        }
    return entry_node


def pop_dialog_state(state: dict) -> dict:
    """Pop the dialog-state stack and return control to the primary assistant."""
    messages = []
    if state.get("messages") and state["messages"][-1].tool_calls:
        messages.append(
            ToolMessage(
                content="Resuming conversation with the main assistant. Please review prior context.",
                tool_call_id=state["messages"][-1].tool_calls[0]["id"],
            )
        )
    return {
        "dialog_state": "pop",
        "messages": messages,
    }


def direct_agent_handoff(source_agent: str, target_entry: str) -> Callable:
    """Build a conditional-edge function for P2P agent handoff."""
    from langgraph.prebuilt import tools_condition
    from app.graph.models import CompleteOrEscalate

    def _route(state: dict) -> str:
        route = tools_condition(state)
        if route == "end":
            from langgraph.constants import END
            return END
        tool_calls = state["messages"][-1].tool_calls
        if not tool_calls:
            return END
        did_handoff = any(
            tc["name"] == CompleteOrEscalate.__name__ for tc in tool_calls
        )
        if did_handoff:
            logger.info("P2P handoff: %s -> %s", source_agent, target_entry)
            return target_entry
        safe_names: set[str] = set()
        if all(tc["name"] in safe_names for tc in tool_calls):
            return f"{source_agent}_safe_tools"
        return f"{source_agent}_sensitive_tools"
    return _route
