"""
routing.py -- Graph Route Functions

All conditional-edge callables used by the main StateGraph.
These functions determine the next node at each branching point.

Exports:
    route_by_intent(state) -> str
    route_primary_assistant(state) -> str
    route_sub_agent(agent_node, safe_tools, sensitive_tools, safe_node, sensitive_node) -> Callable
    route_to_workflow(state) -> str
"""

from __future__ import annotations
import logging
from typing import Callable, List
from langgraph.constants import END
from langgraph.prebuilt import tools_condition
from app.graph.models import CompleteOrEscalate

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Intent-based early routing (fan-out)
# ---------------------------------------------------------------------------

def route_by_intent(state: dict) -> str:
    """Route to sub-agent or primary assistant based on intent_classification.

    This is the fan-out stage: classifier -> route_by_intent -> (sub-agent | primary)
    """
    intent_data = state.get("intent_classification", {})
    intent = intent_data.get("intent", "clarification")

    ROUTE_MAP = {
        "flight": "enter_update_flight",
        "hotel": "enter_book_hotel",
        "car_rental": "enter_book_car_rental",
        "excursion": "enter_book_excursion",
        "multi_domain": "primary_assistant",
        "clarification": "primary_assistant",
    }

    next_node = ROUTE_MAP.get(intent, "primary_assistant")
    logger.debug(
        "route_by_intent: intent=%s confidence=%.2f -> %s",
        intent, intent_data.get("confidence", 0.0), next_node,
    )
    return next_node


# ---------------------------------------------------------------------------
# Primary assistant tool-call routing
# ---------------------------------------------------------------------------

def route_primary_assistant(state: dict) -> str:
    """Route from primary assistant based on LLM tool calls.

    Legacy-compatible routing from graph_gradio.py.
    Returns: sub-agent entry node, primary_assistant_tools, or END.
    """
    route = tools_condition(state)
    if route == END:
        return END

    tool_calls = state["messages"][-1].tool_calls
    if not tool_calls:
        return END

    from app.graph.models import (
        ToFlightBookingAssistant,
        ToBookCarRental,
        ToHotelBookingAssistant,
        ToBookExcursion,
    )

    DELEGATION_MAP = {
        ToFlightBookingAssistant.__name__: "enter_update_flight",
        ToBookCarRental.__name__: "enter_book_car_rental",
        ToHotelBookingAssistant.__name__: "enter_book_hotel",
        ToBookExcursion.__name__: "enter_book_excursion",
    }

    tool_name = tool_calls[0]["name"]
    entry_node = DELEGATION_MAP.get(tool_name)
    if entry_node:
        logger.info("Delegating to sub-agent: %s", entry_node)
        return entry_node

    return "primary_assistant_tools"


# ---------------------------------------------------------------------------
# Sub-agent tool routing (factory)
# ---------------------------------------------------------------------------

def route_sub_agent(
    agent_node: str,
    safe_tools: list,
    sensitive_tools: list,
    safe_node: str,
    sensitive_node: str,
) -> Callable[[dict], str]:
    """Factory that builds a sub-agent route function.

    Eliminates repetitive per-agent closures (76% code reduction).
    """
    def _route(state: dict) -> str:
        route = tools_condition(state)
        if route == END:
            return END

        tool_calls = state["messages"][-1].tool_calls
        if not tool_calls:
            return END

        did_cancel = any(
            tc["name"] == CompleteOrEscalate.__name__ for tc in tool_calls
        )
        if did_cancel:
            logger.info("Sub-agent %s: CompleteOrEscalate -> leave_skill", agent_node)
            return "leave_skill"

        safe_names = {t.name for t in safe_tools}
        if all(tc["name"] in safe_names for tc in tool_calls):
            return safe_node

        return sensitive_node

    return _route


# ---------------------------------------------------------------------------
# Dialog-state resume routing
# ---------------------------------------------------------------------------

def route_to_workflow(state: dict) -> str:
    """Route to active dialog workflow or intent classifier.

    If dialog_state is set (resume after interrupt), go to active sub-agent.
    If not, go to intent_classifier for fresh intent detection.
    """
    dialog_state = state.get("dialog_state")
    if not dialog_state:
        return "intent_classifier"
    active = dialog_state[-1]
    logger.debug("route_to_workflow: resuming %s", active)
    return active
