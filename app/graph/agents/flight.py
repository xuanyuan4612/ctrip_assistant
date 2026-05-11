"""
flight.py - FlightAgent

Handles flight search, booking, update, and cancellation.
Inherits from BaseAgent with retry/timeout/guardrail support.
Binds flight tools and CompleteOrEscalate to the LLM.
"""

import logging

from langchain_core.runnables import RunnableConfig

from app.graph.agents.base import BaseAgent, GuardrailResult
from app.graph.agents.prompts.flight import flight_booking_prompt
from app.graph.models import CompleteOrEscalate
from app.graph.tools.business.flights import search_flights, update_ticket_to_new_flight, cancel_ticket
from app.infrastructure.llm.base import LLMProviderFactory
from app.infrastructure.llm import deepseek as _  # ensure DeepSeekProvider is registered
from app.core.config import settings

logger = logging.getLogger(__name__)

llm = LLMProviderFactory.create(settings.LLM_PROVIDER).get_chat_model()

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Tools
# ---------------------------------------------------------------------------

FLIGHT_SAFE_TOOLS = [search_flights]
FLIGHT_SENSITIVE_TOOLS = [update_ticket_to_new_flight, cancel_ticket]
FLIGHT_ALL_TOOLS = FLIGHT_SAFE_TOOLS + FLIGHT_SENSITIVE_TOOLS + [CompleteOrEscalate]


# ---------------------------------------------------------------------------
# FlightAgent
# ---------------------------------------------------------------------------

class FlightAgent(BaseAgent):
    """
    Specialized agent for flight queries, changes, and bookings.
    
    Safe tools (read-only): search_flights
    Sensitive tools (write): update_ticket_to_new_flight, cancel_ticket
    
    Human-in-the-loop: The graph interrupts before sensitive tools.
    """

    def __init__(self, runnable=None, max_retries: int = 3, timeout: int = 60):
        if runnable is None:
            runnable = self._build_runnable()
        super().__init__(runnable, max_retries=max_retries, timeout=timeout)

    def _build_runnable(self):
        """Build the flight agent runnable."""
        return flight_booking_prompt | llm.bind_tools(FLIGHT_ALL_TOOLS)

    # ------------------------------------------------------------------
    # Guardrail hooks
    # ------------------------------------------------------------------

    def pre_guardrail(self, state: dict, config: RunnableConfig) -> GuardrailResult:
        """Ensure we have user_info for flight context."""
        if not state.get("user_info"):
            logger.warning("Flight agent: no user_info in state")
        return GuardrailResult(passed=True)

    def post_guardrail(
        self, state: dict, config: RunnableConfig, result: dict
    ) -> GuardrailResult:
        return GuardrailResult(passed=True)


# ---------------------------------------------------------------------------
# Exports (for graph construction)
# ---------------------------------------------------------------------------

flight_agent = FlightAgent()
