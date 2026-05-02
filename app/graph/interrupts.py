"""
interrupts.py - Human-in-the-Loop Interrupt Management

Manages sensitive-tool-node interrupts that pause graph execution
for user approval before any write/mutation operation.

Exports:
    InterruptManager
    build_approval_prompt(graph, config) -> str
    is_approval_input(user_input) -> bool
    interrupt_manager (singleton)
"""

from __future__ import annotations
import logging
from typing import List, Optional
from langgraph.graph import StateGraph

logger = logging.getLogger(__name__)


class InterruptManager:
    """Central manager for human-in-the-loop interrupt configuration."""

    SENSITIVE_NODES: List[str] = [
        "update_flight_sensitive_tools",
        "book_car_rental_sensitive_tools",
        "book_hotel_sensitive_tools",
        "book_excursion_sensitive_tools",
    ]

    def __init__(self, extra_nodes: Optional[List[str]] = None):
        self._nodes = list(self.SENSITIVE_NODES)
        if extra_nodes:
            self._nodes.extend(extra_nodes)

    @property
    def interrupt_before(self) -> List[str]:
        return list(self._nodes)

    @property
    def node_count(self) -> int:
        return len(self._nodes)

    def register_node(self, node_name: str) -> None:
        if node_name not in self._nodes:
            self._nodes.append(node_name)
            logger.info("Registered interrupt node: %s", node_name)

    def register_nodes(self, node_names: List[str]) -> None:
        for name in node_names:
            self.register_node(name)

    @staticmethod
    def is_paused(graph: StateGraph, config: dict) -> bool:
        try:
            state = graph.get_state(config)
            return bool(state.next) and any(
                n in InterruptManager.SENSITIVE_NODES for n in state.next
            )
        except Exception:
            return False

    @staticmethod
    def get_paused_nodes(graph: StateGraph, config: dict) -> List[str]:
        try:
            state = graph.get_state(config)
            return list(state.next) if state.next else []
        except Exception:
            return []

    @staticmethod
    def build_prompt(graph: StateGraph, config: dict) -> str:
        """Build an approval prompt summarizing pending tool calls."""
        try:
            state = graph.get_state(config)
            if not state.next:
                return ""
            messages = state.values.get("messages", [])
            parts: List[str] = []
            for msg in reversed(messages):
                if hasattr(msg, "tool_calls") and msg.tool_calls:
                    for tc in msg.tool_calls:
                        args = tc.get("args", {})
                        summary = ", ".join(f"{k}={v}" for k, v in args.items())
                        parts.append(f"  - {tc['""'']name['""'']}({summary})")
                    break
            paused = ", ".join(state.next)
            lines = [
                "AI assistant is about to execute the following operations. Your approval is required:",
                f"About to execute at node(s): [{paused}]",
            ]
            if parts:
                lines.extend(parts)
            else:
                lines.append("  (details not available)")
            lines.append("")
            lines.append("Enter 'y' to approve, or describe your requested changes.")
            return "\n".join(lines)
        except Exception as exc:
            logger.warning("build_prompt failed: %s", exc)
            return "AI assistant is ready to execute. Enter 'y' to approve."


def build_approval_prompt(graph: StateGraph, config: dict) -> str:
    return InterruptManager.build_prompt(graph, config)


def is_approval_input(user_input: str) -> bool:
    return user_input.strip().lower() == "y"


interrupt_manager = InterruptManager()
