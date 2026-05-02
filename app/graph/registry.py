"""
registry.py -- Agent Registry

Dynamic agent discovery and sub-graph building for 8+ agent scalability.
Rather than hard-coding sub-graphs, the registry maintains AgentSpec entries.

Exports:
    AgentSpec
    AgentRegistry
    registry (singleton, pre-populated with 4 core agents)
    create_default_registry() -> AgentRegistry
"""

from __future__ import annotations
import logging
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set
from langgraph.graph import StateGraph
from app.graph.agents.base import BaseAgent
from app.graph.handoff import create_entry_node, pop_dialog_state
from app.graph.routing import route_sub_agent
from app.graph.tools.handler import create_tool_node_with_fallback

logger = logging.getLogger(__name__)


@dataclass
class AgentSpec:
    """Complete specification for one sub-agent sub-graph."""
    name: str
    display_name: str
    dialog_state_key: str
    agent: BaseAgent
    safe_tools: list
    sensitive_tools: list
    intents: Set[str] = field(default_factory=set)
    entry_node: str = ""
    agent_node: str = ""
    safe_tools_node: str = ""
    sensitive_tools_node: str = ""

    def __post_init__(self):
        if not self.entry_node:
            self.entry_node = f"enter_{self.name}"
        if not self.agent_node:
            self.agent_node = self.name
        if not self.safe_tools_node:
            self.safe_tools_node = f"{self.name}_safe_tools"
        if not self.sensitive_tools_node:
            self.sensitive_tools_node = f"{self.name}_sensitive_tools"

    def __hash__(self) -> int:
        return hash(self.name)


class AgentRegistry:
    """Dynamic agent registry for scalable multi-agent orchestration."""

    def __init__(self):
        self._specs: Dict[str, AgentSpec] = {}
        self._intent_map: Dict[str, str] = {}

    def register(self, spec: AgentSpec) -> None:
        if spec.name in self._specs:
            logger.warning("Overwriting existing agent spec: %s", spec.name)
        self._specs[spec.name] = spec
        for intent in spec.intents:
            self._intent_map[intent] = spec.entry_node
        logger.info("Registered agent '%s' (intents: %s)", spec.name, ", ".join(spec.intents) if spec.intents else "none")

    def unregister(self, name: str) -> None:
        spec = self._specs.pop(name, None)
        if spec:
            for intent in spec.intents:
                self._intent_map.pop(intent, None)
            logger.info("Unregistered agent: %s", name)

    def get(self, name: str) -> Optional[AgentSpec]:
        return self._specs.get(name)

    def list_agents(self) -> List[str]:
        return list(self._specs.keys())

    def count(self) -> int:
        return len(self._specs)

    def intent_route_map(self) -> Dict[str, str]:
        return dict(self._intent_map)

    def interrupt_nodes(self) -> List[str]:
        return [spec.sensitive_tools_node for spec in self._specs.values()]

    def all_entry_nodes(self) -> List[str]:
        return [spec.entry_node for spec in self._specs.values()]

    def build_sub_graph(self, builder: StateGraph, spec: AgentSpec) -> StateGraph:
        """Build one parameterised sub-agent sub-graph."""
        builder.add_node(
            spec.entry_node,
            create_entry_node(spec.display_name, spec.dialog_state_key),
        )
        builder.add_node(spec.agent_node, spec.agent)
        builder.add_edge(spec.entry_node, spec.agent_node)
        builder.add_node(
            spec.safe_tools_node,
            create_tool_node_with_fallback(spec.safe_tools),
        )
        builder.add_node(
            spec.sensitive_tools_node,
            create_tool_node_with_fallback(spec.sensitive_tools),
        )
        route_fn = route_sub_agent(
            agent_node=spec.agent_node,
            safe_tools=spec.safe_tools,
            sensitive_tools=spec.sensitive_tools,
            safe_node=spec.safe_tools_node,
            sensitive_node=spec.sensitive_tools_node,
        )
        builder.add_edge(spec.safe_tools_node, spec.agent_node)
        builder.add_edge(spec.sensitive_tools_node, spec.agent_node)
        builder.add_conditional_edges(
            spec.agent_node,
            route_fn,
            [spec.safe_tools_node, spec.sensitive_tools_node, "leave_skill", "__end__"],
        )
        return builder

    def build_all(self, builder: StateGraph) -> StateGraph:
        """Build sub-graphs for ALL registered agents."""
        if "leave_skill" not in builder.nodes:
            builder.add_node("leave_skill", pop_dialog_state)
        for spec in self._specs.values():
            builder = self.build_sub_graph(builder, spec)
        try:
            builder.add_edge("leave_skill", "primary_assistant")
        except Exception:
            pass
        return builder


def create_default_registry() -> AgentRegistry:
    """Pre-populated registry with the 4 core agents."""
    from app.graph.agents import (
        flight_agent, FLIGHT_SAFE_TOOLS, FLIGHT_SENSITIVE_TOOLS,
        hotel_agent, HOTEL_SAFE_TOOLS, HOTEL_SENSITIVE_TOOLS,
        car_rental_agent, CAR_RENTAL_SAFE_TOOLS, CAR_RENTAL_SENSITIVE_TOOLS,
        excursion_agent, EXCURSION_SAFE_TOOLS, EXCURSION_SENSITIVE_TOOLS,
    )

    reg = AgentRegistry()
    reg.register(AgentSpec(
        name="update_flight",
        display_name="Flight Updates & Booking Assistant",
        dialog_state_key="update_flight",
        agent=flight_agent,
        safe_tools=FLIGHT_SAFE_TOOLS,
        sensitive_tools=FLIGHT_SENSITIVE_TOOLS,
        intents={"flight"},
        entry_node="enter_update_flight",
        agent_node="update_flight",
        safe_tools_node="update_flight_safe_tools",
        sensitive_tools_node="update_flight_sensitive_tools",
    ))
    reg.register(AgentSpec(
        name="book_car_rental",
        display_name="Car Rental Assistant",
        dialog_state_key="book_car_rental",
        agent=car_rental_agent,
        safe_tools=CAR_RENTAL_SAFE_TOOLS,
        sensitive_tools=CAR_RENTAL_SENSITIVE_TOOLS,
        intents={"car_rental"},
        entry_node="enter_book_car_rental",
        agent_node="book_car_rental",
        safe_tools_node="book_car_rental_safe_tools",
        sensitive_tools_node="book_car_rental_sensitive_tools",
    ))
    reg.register(AgentSpec(
        name="book_hotel",
        display_name="Hotel Booking Assistant",
        dialog_state_key="book_hotel",
        agent=hotel_agent,
        safe_tools=HOTEL_SAFE_TOOLS,
        sensitive_tools=HOTEL_SENSITIVE_TOOLS,
        intents={"hotel"},
        entry_node="enter_book_hotel",
        agent_node="book_hotel",
        safe_tools_node="book_hotel_safe_tools",
        sensitive_tools_node="book_hotel_sensitive_tools",
    ))
    reg.register(AgentSpec(
        name="book_excursion",
        display_name="Trip Recommendation Assistant",
        dialog_state_key="book_excursion",
        agent=excursion_agent,
        safe_tools=EXCURSION_SAFE_TOOLS,
        sensitive_tools=EXCURSION_SENSITIVE_TOOLS,
        intents={"excursion"},
        entry_node="enter_book_excursion",
        agent_node="book_excursion",
        safe_tools_node="book_excursion_safe_tools",
        sensitive_tools_node="book_excursion_sensitive_tools",
    ))
    return reg


registry = create_default_registry()