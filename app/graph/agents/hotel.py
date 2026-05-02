"""
hotel.py - HotelAgent

Handles hotel search, booking, modification, and cancellation.
Inherits from BaseAgent with retry/timeout/guardrail support.
Binds hotel tools and CompleteOrEscalate to the LLM.
"""

import logging

from langchain_core.runnables import RunnableConfig

from app.graph.agents.base import BaseAgent, GuardrailResult
from app.graph.agents.prompts.hotel import book_hotel_prompt
from graph_chat.base_data_model import CompleteOrEscalate
from graph_chat.llm_tavily import llm
from tools.hotels_tools import search_hotels, book_hotel, update_hotel, cancel_hotel

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Tools
# ---------------------------------------------------------------------------

HOTEL_SAFE_TOOLS = [search_hotels]
HOTEL_SENSITIVE_TOOLS = [book_hotel, update_hotel, cancel_hotel]
HOTEL_ALL_TOOLS = HOTEL_SAFE_TOOLS + HOTEL_SENSITIVE_TOOLS + [CompleteOrEscalate]


# ---------------------------------------------------------------------------
# HotelAgent
# ---------------------------------------------------------------------------

class HotelAgent(BaseAgent):
    """
    Specialized agent for hotel reservations.
    
    Safe tools (read-only): search_hotels
    Sensitive tools (write): book_hotel, update_hotel, cancel_hotel
    
    Human-in-the-loop: The graph interrupts before sensitive tools.
    """

    def __init__(self, runnable=None, max_retries: int = 3, timeout: int = 60):
        if runnable is None:
            runnable = self._build_runnable()
        super().__init__(runnable, max_retries=max_retries, timeout=timeout)

    def _build_runnable(self):
        """Build the hotel agent runnable."""
        return book_hotel_prompt | llm.bind_tools(HOTEL_ALL_TOOLS)

    # ------------------------------------------------------------------
    # Guardrail hooks
    # ------------------------------------------------------------------

    def pre_guardrail(self, state: dict, config: RunnableConfig) -> GuardrailResult:
        return GuardrailResult(passed=True)

    def post_guardrail(
        self, state: dict, config: RunnableConfig, result: dict
    ) -> GuardrailResult:
        return GuardrailResult(passed=True)


# ---------------------------------------------------------------------------
# Exports
# ---------------------------------------------------------------------------

hotel_agent = HotelAgent()
