"""
primary.py - PrimaryAgent (Supervisor/Router)

The primary agent is the entry point for all user requests.
It uses IntentClassifier for intent detection instead of LLM tool calling,
then routes to the appropriate sub-agent or handles the request itself.

Inherits from BaseAgent with retry/timeout/guardrail support.
"""

import logging
from typing import Optional

from langchain_core.runnables import RunnableConfig
from langchain_openai import ChatOpenAI

from app.graph.agents.base import BaseAgent, GuardrailResult
from app.graph.agents.classifier import IntentClassifier
from app.graph.agents.prompts.primary import primary_assistant_prompt
from app.graph.agents.router import default_router, ModelRouter
from graph_chat.base_data_model import (
    ToFlightBookingAssistant,
    ToBookCarRental,
    ToHotelBookingAssistant,
    ToBookExcursion,
)
from graph_chat.llm_tavily import tavily_tool, llm
from tools.flights_tools import search_flights
from tools.retriever_vector import lookup_policy

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Default tools for the primary assistant
# ---------------------------------------------------------------------------

PRIMARY_TOOLS = [
    tavily_tool,
    search_flights,
    lookup_policy,
]

DELEGATION_TOOLS = [
    ToFlightBookingAssistant,
    ToBookCarRental,
    ToHotelBookingAssistant,
    ToBookExcursion,
]

ALL_PRIMARY_TOOLS = PRIMARY_TOOLS + DELEGATION_TOOLS


# ---------------------------------------------------------------------------
# PrimaryAgent
# ---------------------------------------------------------------------------

class PrimaryAgent(BaseAgent):
    """
    Primary (supervisor) agent that:
      1. Classifies intent via IntentClassifier (cheap model)
      2. Routes to sub-agents or handles directly
      3. Uses ModelRouter for complexity-based model selection
    
    If intent is clarification or flight-info, handles directly.
    If intent is a specific domain, delegates via tool call.
    If intent is multi_domain, uses a more capable model.
    """

    def __init__(
        self,
        runnable=None,
        classifier: Optional[IntentClassifier] = None,
        router: Optional[ModelRouter] = None,
        max_retries: int = 3,
        timeout: int = 60,
    ):
        if runnable is None:
            runnable = self._build_runnable()
        super().__init__(runnable, max_retries=max_retries, timeout=timeout)
        self.classifier = classifier or IntentClassifier()
        self.router = router or default_router

    def _build_runnable(self):
        """Build the default primary assistant runnable."""
        return primary_assistant_prompt | llm.bind_tools(ALL_PRIMARY_TOOLS)

    # ------------------------------------------------------------------
    # Override: node callable with intent classification
    # ------------------------------------------------------------------

    def __call__(self, state: dict, config: RunnableConfig) -> dict:
        """
        Override __call__ to inject intent classification before invocation.
        
        The intent is stored in state so the graph router can use it
        instead of relying solely on LLM tool calls.
        """
        # Classify intent
        messages = state.get("messages", [])
        last_human = ""
        for msg in reversed(messages):
            if hasattr(msg, "type") and msg.type == "human":
                last_human = msg.content
                break

        if last_human:
            intent_result = self.classifier.classify(last_human)
            state["intent_classification"] = intent_result
            logger.info(
                "Classified intent: %s (confidence=%.2f)",
                intent_result.get("intent"),
                intent_result.get("confidence", 0),
            )

        # Route model based on complexity
        model_tier = self.router.route(state)
        logger.info("Model tier selected: %s", model_tier)

        # For multi_domain or complex intents, use a stronger model
        intent = state.get("intent_classification", {}).get("intent", "")
        if intent == "multi_domain" or model_tier in ("medium", "expensive"):
            state["_model_tier"] = model_tier
            # Re-build runnable with better model if needed
            if model_tier != "cheap":
                better_llm = self.router.select_llm(state)
                self.runnable = primary_assistant_prompt | better_llm.bind_tools(ALL_PRIMARY_TOOLS)

        return self.invoke(state, config)

    # ------------------------------------------------------------------
    # Guardrail hooks
    # ------------------------------------------------------------------

    def pre_guardrail(self, state: dict, config: RunnableConfig) -> GuardrailResult:
        """Reject empty messages."""
        messages = state.get("messages", [])
        if not messages:
            return GuardrailResult(passed=False, reason="No messages provided.")
        return GuardrailResult(passed=True)

    def post_guardrail(
        self, state: dict, config: RunnableConfig, result: dict
    ) -> GuardrailResult:
        """Validate that the output contains meaningful content."""
        messages = result.get("messages", [])
        if not messages:
            return GuardrailResult(passed=False, reason="Empty response from agent.")
        return GuardrailResult(passed=True)


# ---------------------------------------------------------------------------
# Singleton
# ---------------------------------------------------------------------------

primary_agent = PrimaryAgent()
