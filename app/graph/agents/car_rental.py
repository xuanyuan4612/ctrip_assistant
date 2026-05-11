"""
car_rental.py - CarRentalAgent

Handles car rental search, booking, modification, and cancellation.
Inherits from BaseAgent with retry/timeout/guardrail support.
Binds car rental tools and CompleteOrEscalate to the LLM.
"""

import logging

from langchain_core.runnables import RunnableConfig

from app.graph.agents.base import BaseAgent, GuardrailResult
from app.graph.agents.prompts.car_rental import book_car_rental_prompt
from app.graph.models import CompleteOrEscalate
from app.graph.tools.business.car_rentals import search_car_rentals, book_car_rental, update_car_rental, cancel_car_rental
from app.infrastructure.llm.base import LLMProviderFactory
from app.infrastructure.llm import deepseek as _
from app.core.config import settings

logger = logging.getLogger(__name__)

llm = LLMProviderFactory.create(settings.LLM_PROVIDER).get_chat_model()

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Tools
# ---------------------------------------------------------------------------

CAR_RENTAL_SAFE_TOOLS = [search_car_rentals]
CAR_RENTAL_SENSITIVE_TOOLS = [book_car_rental, update_car_rental, cancel_car_rental]
CAR_RENTAL_ALL_TOOLS = CAR_RENTAL_SAFE_TOOLS + CAR_RENTAL_SENSITIVE_TOOLS + [CompleteOrEscalate]


# ---------------------------------------------------------------------------
# CarRentalAgent
# ---------------------------------------------------------------------------

class CarRentalAgent(BaseAgent):
    """
    Specialized agent for car rental reservations.
    
    Safe tools (read-only): search_car_rentals
    Sensitive tools (write): book_car_rental, update_car_rental, cancel_car_rental
    
    Human-in-the-loop: The graph interrupts before sensitive tools.
    """

    def __init__(self, runnable=None, max_retries: int = 3, timeout: int = 60):
        if runnable is None:
            runnable = self._build_runnable()
        super().__init__(runnable, max_retries=max_retries, timeout=timeout)

    def _build_runnable(self):
        """Build the car rental agent runnable."""
        return book_car_rental_prompt | llm.bind_tools(CAR_RENTAL_ALL_TOOLS)

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

car_rental_agent = CarRentalAgent()
