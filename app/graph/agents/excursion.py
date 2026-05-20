"""
excursion.py - ExcursionAgent

Handles trip recommendations, excursion search, booking, and cancellation.
Inherits from BaseAgent with retry/timeout/guardrail support.
Binds excursion tools and CompleteOrEscalate to the LLM.
"""

import logging

from langchain_core.runnables import RunnableConfig

from app.graph.agents.base import BaseAgent, GuardrailResult
from app.graph.agents.prompts.excursion import book_excursion_prompt
from app.graph.models import CompleteOrEscalate
from app.graph.tools.business.excursions import search_trip_recommendations, book_excursion, update_excursion, cancel_excursion
from app.infrastructure.llm.base import LLMProviderFactory
from app.infrastructure.llm import deepseek as _
from app.core.config import settings

logger = logging.getLogger(__name__)

llm = LLMProviderFactory.create(settings.LLM_PROVIDER).get_chat_model()

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Tools
# ---------------------------------------------------------------------------

EXCURSION_SAFE_TOOLS = [search_trip_recommendations]
EXCURSION_SENSITIVE_TOOLS = [book_excursion, update_excursion, cancel_excursion]
EXCURSION_ALL_TOOLS = EXCURSION_SAFE_TOOLS + EXCURSION_SENSITIVE_TOOLS + [CompleteOrEscalate]


# ---------------------------------------------------------------------------
# ExcursionAgent
# ---------------------------------------------------------------------------

class ExcursionAgent(BaseAgent):
    """
    Specialized agent for trip recommendations and excursion bookings.
    
    Safe tools (read-only): search_trip_recommendations
    Sensitive tools (write): book_excursion, update_excursion, cancel_excursion
    
    Human-in-the-loop: The graph interrupts before sensitive tools.
    """

    def __init__(self, runnable=None, max_retries: int = 3, timeout: int = 60):
        if runnable is None:
            runnable = self._build_runnable()
        super().__init__(runnable, max_retries=max_retries, timeout=timeout)

    def _build_runnable(self):
        """Build the excursion agent runnable."""
        return book_excursion_prompt | llm.bind_tools(EXCURSION_ALL_TOOLS)

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

excursion_agent = ExcursionAgent()
