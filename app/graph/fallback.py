"""
fallback.py - Degradation Chain

Implements a multi-tier fallback strategy for the graph's tool nodes::

    LLM -> Cache -> Rules -> Human

Each tier is tried in sequence when the previous one fails.

Exports:
    FallbackChain
    llm_fallback, cache_fallback, rules_fallback, human_fallback
    create_fallback_tool_node(tools) -> ToolNode
    fallback_chain (singleton)
"""

from __future__ import annotations
import json
import logging
from enum import Enum, auto
from typing import Any, Callable, Dict, List, Optional, Tuple
from langchain_core.messages import ToolMessage
from langchain_core.runnables import RunnableLambda
from langgraph.prebuilt import ToolNode
from app.graph.tools.handler import create_tool_node_with_fallback

logger = logging.getLogger(__name__)


class FallbackTier(Enum):
    LLM = auto()
    CACHE = auto()
    RULES = auto()
    HUMAN = auto()


class FallbackChain:
    """Configurable degradation chain for tool execution."""

    def __init__(
        self,
        cache_store: Optional[Dict[str, Any]] = None,
        rules: Optional[List[Callable]] = None,
        tier_order: Optional[List[FallbackTier]] = None,
    ):
        self._cache: Dict[str, Any] = cache_store if cache_store is not None else {}
        self._rules: List[Callable] = rules or []
        self._tier_order = tier_order or [
            FallbackTier.LLM,
            FallbackTier.CACHE,
            FallbackTier.RULES,
            FallbackTier.HUMAN,
        ]

    def execute(
        self,
        tool_name: str,
        args: Dict[str, Any],
        llm_invoke: Optional[Callable[[], Any]] = None,
    ) -> Any:
        """Execute the tool through the degradation chain."""
        errors: List[Tuple[FallbackTier, str]] = []

        for tier in self._tier_order:
            try:
                if tier == FallbackTier.LLM:
                    result = self._try_llm(tool_name, args, llm_invoke)
                elif tier == FallbackTier.CACHE:
                    result = self._try_cache(tool_name, args)
                elif tier == FallbackTier.RULES:
                    result = self._try_rules(tool_name, args)
                elif tier == FallbackTier.HUMAN:
                    result = self._try_human(tool_name, args)
                else:
                    continue

                if result is not None:
                    logger.info("FallbackChain: tier=%s succeeded for %s",
                                tier.name, tool_name)
                    return result

            except Exception as exc:
                msg = f"{type(exc).__name__}: {exc}"
                errors.append((tier, msg))
                logger.warning("FallbackChain: tier=%s failed for %s: %s",
                               tier.name, tool_name, msg)

        detail = "; ".join(f"{t.name}: {e}" for t, e in errors)
        raise RuntimeError(
            f"All fallback tiers exhausted for tool '{tool_name}': {detail}"
        )

    def get_cached(self, tool_name: str, args: Dict[str, Any]) -> Optional[Any]:
        key = self._cache_key(tool_name, args)
        return self._cache.get(key)

    def set_cached(self, tool_name: str, args: Dict[str, Any], value: Any) -> None:
        key = self._cache_key(tool_name, args)
        self._cache[key] = value

    def _try_llm(self, tool_name: str, args: Dict[str, Any],
                  llm_invoke: Optional[Callable[[], Any]]) -> Any:
        if llm_invoke is None:
            raise ValueError("LLM tier requires an invoke callable")
        return llm_invoke()

    def _try_cache(self, tool_name: str, args: Dict[str, Any]) -> Any:
        key = self._cache_key(tool_name, args)
        cached = self._cache.get(key)
        if cached is not None:
            logger.debug("Cache hit: %s", key)
        return cached

    def _try_rules(self, tool_name: str, args: Dict[str, Any]) -> Any:
        for rule in self._rules:
            result = rule(tool_name, args)
            if result is not None:
                return result
        return None

    def _try_human(self, tool_name: str, args: Dict[str, Any]) -> Any:
        raise HumanInterventionRequired(tool_name, args)

    @staticmethod
    def _cache_key(tool_name: str, args: Dict[str, Any]) -> str:
        return f"{tool_name}:{json.dumps(args, sort_keys=True, default=str)}"


class HumanInterventionRequired(Exception):
    """Raised when the fallback chain exhausts all automated tiers."""
    def __init__(self, tool_name: str, args: Dict[str, Any]):
        self.tool_name = tool_name
        self.args = args
        super().__init__(f"Human intervention required for tool '{tool_name}'")


def llm_fallback(state: dict) -> dict:
    error = state.get("error", "Unknown error")
    tool_calls = state["messages"][-1].tool_calls
    logger.warning("LLM fallback triggered: %s", error)
    return {
        "messages": [
            ToolMessage(
                content=f"System temporarily unavailable. Please retry later. (Error: {error})",
                tool_call_id=tc["id"],
            )
            for tc in tool_calls
        ]
    }


def cache_fallback(state: dict) -> dict:
    logger.info("Cache fallback invoked (not yet implemented)")
    return _fallback_error(state, "Cache tier not available")


def rules_fallback(state: dict) -> dict:
    logger.info("Rules fallback invoked (not yet implemented)")
    return _fallback_error(state, "Rules tier not available")


def human_fallback(state: dict) -> dict:
    logger.warning("Human fallback invoked - all automated tiers failed")
    return _fallback_error(state, "All automated processing failed. Please contact customer service.")


def _fallback_error(state: dict, message: str) -> dict:
    tool_calls = state["messages"][-1].tool_calls
    return {
        "messages": [
            ToolMessage(content=message, tool_call_id=tc["id"])
            for tc in tool_calls
        ]
    }


def create_fallback_tool_node(tools: list) -> ToolNode:
    """Create a ToolNode with multi-tier fallback."""
    return create_tool_node_with_fallback(tools).with_fallbacks(
        [
            RunnableLambda(cache_fallback),
            RunnableLambda(rules_fallback),
            RunnableLambda(human_fallback),
        ],
        exception_key="error",
    )


fallback_chain = FallbackChain()
