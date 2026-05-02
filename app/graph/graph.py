"""
graph.py - Main Graph Builder

Constructs the enhanced multi-agent StateGraph that wires together
all agents, tools, and routing logic.

Pipeline:
    START -> fetch_user_info
         -> route_to_workflow
              |-> intent_classifier (if new conversation)
              |    -> route_by_intent (fan-out)
              |         |-> sub-agent entry nodes
              |         |-> primary_assistant
              |-> sub-agent agent nodes (if resuming)
    primary_assistant -> route_primary_assistant
              |-> sub-agent entry nodes
              |-> primary_assistant_tools -> primary_assistant (loop)
    sub-agent -> route_sub_agent
              |-> safe_tools -> agent (loop)
              |-> sensitive_tools -> agent (loop)  [INTERRUPT before]
              |-> leave_skill -> primary_assistant
    primary_assistant -> END

Exports:
    build_sub_graph(builder, spec) -> StateGraph
    build_graph() -> CompiledStateGraph
    build_default_graph() -> CompiledStateGraph
    SubAgentSpec
"""

from __future__ import annotations
import logging
from typing import List, Optional
from langgraph.checkpoint.memory import MemorySaver
from langgraph.constants import END, START
from langgraph.graph import StateGraph
from app.graph.state import State
from app.graph.agents import primary_agent, ALL_PRIMARY_TOOLS, IntentClassifier
from app.graph.tools.handler import create_tool_node_with_fallback
from app.graph.handoff import create_entry_node, pop_dialog_state
from app.graph.routing import (
    route_by_intent,
    route_primary_assistant,
    route_sub_agent,
    route_to_workflow,
)
from app.graph.interrupts import InterruptManager, interrupt_manager
from app.graph.lifecycle import load_user_info, extract_memories
from app.graph.registry import AgentSpec, registry

logger = logging.getLogger(__name__)

# Convenience alias
SubAgentSpec = AgentSpec


def build_sub_graph(builder: StateGraph, spec: AgentSpec) -> StateGraph:
    """Build one parameterised sub-agent sub-graph.

    This parameterised factory eliminates the 76% code duplication
    between the 4 legacy sub-graph builders in build_child_graph.py.

    Topology: entry_node -> agent_node -> (safe_tools | sensitive_tools | leave_skill)
    """
    # Entry node
    builder.add_node(
        spec.entry_node,
        create_entry_node(spec.display_name, spec.dialog_state_key),
    )

    # Agent node
    builder.add_node(spec.agent_node, spec.agent)
    builder.add_edge(spec.entry_node, spec.agent_node)

    # Tool nodes
    builder.add_node(
        spec.safe_tools_node,
        create_tool_node_with_fallback(spec.safe_tools),
    )
    builder.add_node(
        spec.sensitive_tools_node,
        create_tool_node_with_fallback(spec.sensitive_tools),
    )

    # Route function (parameterised)
    route_fn = route_sub_agent(
        agent_node=spec.agent_node,
        safe_tools=spec.safe_tools,
        sensitive_tools=spec.sensitive_tools,
        safe_node=spec.safe_tools_node,
        sensitive_node=spec.sensitive_tools_node,
    )

    # Edges
    builder.add_edge(spec.safe_tools_node, spec.agent_node)
    builder.add_edge(spec.sensitive_tools_node, spec.agent_node)
    builder.add_conditional_edges(
        spec.agent_node,
        route_fn,
        [spec.safe_tools_node, spec.sensitive_tools_node, "leave_skill", END],
    )

    logger.debug("Built sub-graph: %s", spec.name)
    return builder


def build_graph(
    use_registry: bool = True,
    extra_interrupt_nodes: Optional[List[str]] = None,
    enable_memory_extraction: bool = False,
) -> StateGraph:
    """Build the complete enhanced multi-agent StateGraph.

    Args:
        use_registry: If True (default), build sub-graphs from AgentRegistry.
        extra_interrupt_nodes: Additional sensitive-tool nodes to interrupt before.
        enable_memory_extraction: If True, add extract_memories node (future).

    Returns:
        Compiled StateGraph ready for streaming/invocation.
    """
    # --------------------------------------------------------------
    # 1. Create the StateGraph
    # --------------------------------------------------------------
    builder = StateGraph(State)

    # --------------------------------------------------------------
    # 2. Fetch user info (START node)
    # --------------------------------------------------------------
    builder.add_node("fetch_user_info", load_user_info)
    builder.add_edge(START, "fetch_user_info")

    # --------------------------------------------------------------
    # 3. Intent classifier (early intent detection)
    # --------------------------------------------------------------
    classifier = IntentClassifier().as_node()
    builder.add_node("intent_classifier", classifier)

    # --------------------------------------------------------------
    # 4. Shared leave_skill node
    # --------------------------------------------------------------
    builder.add_node("leave_skill", pop_dialog_state)

    # --------------------------------------------------------------
    # 5. Build sub-graphs from registry
    # --------------------------------------------------------------
    if use_registry:
        for name in registry.list_agents():
            spec = registry.get(name)
            if spec:
                builder = build_sub_graph(builder, spec)

    # Wire leave_skill -> primary_assistant
    builder.add_edge("leave_skill", "primary_assistant")

    # --------------------------------------------------------------
    # 6. Primary assistant and tools
    # --------------------------------------------------------------
    builder.add_node("primary_assistant", primary_agent)
    builder.add_node(
        "primary_assistant_tools",
        create_tool_node_with_fallback(ALL_PRIMARY_TOOLS),
    )

    # --------------------------------------------------------------
    # 7. Conditional edges (routing)
    # --------------------------------------------------------------

    # 7a. fetch_user_info -> route_to_workflow
    wf_targets = {
        "intent_classifier": "intent_classifier",
        "update_flight": "update_flight",
        "book_car_rental": "book_car_rental",
        "book_hotel": "book_hotel",
        "book_excursion": "book_excursion",
    }
    builder.add_conditional_edges("fetch_user_info", route_to_workflow, wf_targets)

    # 7b. intent_classifier -> route_by_intent (fan-out)
    intent_targets = {
        "enter_update_flight": "enter_update_flight",
        "enter_book_car_rental": "enter_book_car_rental",
        "enter_book_hotel": "enter_book_hotel",
        "enter_book_excursion": "enter_book_excursion",
        "primary_assistant": "primary_assistant",
    }
    builder.add_conditional_edges("intent_classifier", route_by_intent, intent_targets)

    # 7c. primary_assistant -> route_primary_assistant
    delegate_targets = {
        "enter_update_flight": "enter_update_flight",
        "enter_book_car_rental": "enter_book_car_rental",
        "enter_book_hotel": "enter_book_hotel",
        "enter_book_excursion": "enter_book_excursion",
        "primary_assistant_tools": "primary_assistant_tools",
        END: END,
    }
    builder.add_conditional_edges("primary_assistant", route_primary_assistant, delegate_targets)

    # 7d. Tool node loops back to primary
    builder.add_edge("primary_assistant_tools", "primary_assistant")

    # --------------------------------------------------------------
    # 8. Optional: extract_memories at end (future)
    # --------------------------------------------------------------
    if enable_memory_extraction:
        builder.add_node("extract_memories", extract_memories)
        # Wiring to be added when memory extraction is implemented

    # --------------------------------------------------------------
    # 9. Compile with checkpointer and interrupts
    # --------------------------------------------------------------
    memory = MemorySaver()

    if extra_interrupt_nodes:
        interrupt_manager.register_nodes(extra_interrupt_nodes)

    graph = builder.compile(
        checkpointer=memory,
        interrupt_before=interrupt_manager.interrupt_before,
    )

    logger.info(
        "Graph compiled: %d sub-agents, %d interrupt nodes",
        registry.count(),
        interrupt_manager.node_count,
    )

    return graph


def build_default_graph() -> StateGraph:
    """Build and return the default compiled graph."""
    return build_graph(use_registry=True, enable_memory_extraction=False)