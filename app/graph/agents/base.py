"""
base.py — BaseAgent

Production base class for all LangGraph agents.
Provides retry logic (exponential backoff), timeout enforcement,
and guardrail hooks that can be overridden by subclasses.
"""

import asyncio
import logging
import time
from typing import Any, Callable, Optional, Protocol

from langchain_core.runnables import Runnable, RunnableConfig

logger = logging.getLogger(__name__)


class GuardrailResult:
    """Result returned by a guardrail hook."""

    def __init__(self, passed: bool, reason: str = ""):
        self.passed = passed
        self.reason = reason

    def __bool__(self):
        return self.passed


class GuardrailHook(Protocol):
    """Protocol for guardrail hooks."""

    def __call__(self, state: dict, config: RunnableConfig) -> GuardrailResult:
        ...


class BaseAgent:
    """
    Production base agent with retry, timeout, and guardrail support.

    Usage::

        class MyAgent(BaseAgent):
            def __init__(self, runnable, **kwargs):
                super().__init__(runnable, **kwargs)

            def pre_guardrail(self, state, config) -> GuardrailResult:
                # custom guardrail logic
                return GuardrailResult(passed=True)

    The invoke flow:
        1. pre_guardrail hook  -  reject early if guardrail fails
        2. retry loop          -  max_retries attempts with exponential backoff
        3. post_guardrail hook -  validate output before returning
    """

    def __init__(
        self,
        runnable: Runnable,
        guardrail: Optional[GuardrailHook] = None,
        max_retries: int = 3,
        timeout: int = 60,
    ):
        self.runnable = runnable
        self._guardrail = guardrail
        self.max_retries = max_retries
        self.timeout = timeout

    # ------------------------------------------------------------------
    # Guardrail hooks (override in subclasses)
    # ------------------------------------------------------------------

    def pre_guardrail(self, state: dict, config: RunnableConfig) -> GuardrailResult:
        """Called BEFORE invoking the runnable. Return failed to reject input."""
        if self._guardrail is not None:
            return self._guardrail(state, config)
        return GuardrailResult(passed=True)

    def post_guardrail(
        self, state: dict, config: RunnableConfig, result: dict
    ) -> GuardrailResult:
        """Called AFTER the runnable returns. Return failed to retry or escalate."""
        return GuardrailResult(passed=True)

    # ------------------------------------------------------------------
    # Main invoke
    # ------------------------------------------------------------------

    def __call__(self, state: dict, config: RunnableConfig) -> dict:
        """Callable interface for LangGraph nodes."""
        return self.invoke(state, config)

    def invoke(self, state: dict, config: RunnableConfig) -> dict:
        """
        Invoke the agent with retry loop, exponential backoff, and guardrails.

        Flow:
          1. pre_guardrail check
          2. retry loop (max_retries attempts):
             a. run the LLM with timeout
             b. post_guardrail check
             c. if output is empty/invalid, retry with a prompt
          3. return result
        """
        # ---- 1. Pre-guardrail ----
        guard = self.pre_guardrail(state, config)
        if not guard:
            logger.warning("Pre-guardrail rejected: %s", guard.reason)
            return self._build_rejection(guard.reason)

        # ---- 2. Retry loop ----
        last_exception: Optional[Exception] = None

        for attempt in range(1, self.max_retries + 1):
            try:
                result = self._invoke_with_timeout(state, config)

                # ---- 3. Post-guardrail ----
                guard = self.post_guardrail(state, config, result)
                if not guard:
                    logger.warning(
                        "Post-guardrail failed (attempt %d/%d): %s",
                        attempt,
                        self.max_retries,
                        guard.reason,
                    )
                    state = self._enrich_state_for_retry(state, guard.reason)
                    continue

                # ---- Validate output ----
                messages = result.get("messages", [])
                if not messages:
                    state = self._enrich_state_for_retry(
                        state, "Please provide a real output as response."
                    )
                    continue

                last_msg = messages[-1] if isinstance(messages, list) else messages
                if hasattr(last_msg, "tool_calls") and not last_msg.tool_calls:
                    content = last_msg.content
                    if not content:
                        state = self._enrich_state_for_retry(
                            state, "Please provide a real output as response."
                        )
                        continue
                    if isinstance(content, list) and (
                        not content[0].get("text") if content else True
                    ):
                        state = self._enrich_state_for_retry(
                            state, "Please provide a real output as response."
                        )
                        continue

                return result

            except asyncio.TimeoutError:
                logger.error("Timeout on attempt %d/%d", attempt, self.max_retries)
                last_exception = asyncio.TimeoutError("LLM call timed out")
                if attempt < self.max_retries:
                    self._sleep_backoff(attempt)
                continue

            except Exception as exc:
                logger.error(
                    "Error on attempt %d/%d: %s", attempt, self.max_retries, exc
                )
                last_exception = exc
                if attempt < self.max_retries:
                    self._sleep_backoff(attempt)
                continue

        # All retries exhausted
        error_msg = f"Agent failed after {self.max_retries} attempts"
        if last_exception:
            error_msg += f": {last_exception}"
        logger.error(error_msg)
        return self._build_error_response(error_msg)

    def _invoke_with_timeout(
        self, state: dict, config: RunnableConfig
    ) -> dict:
        """Invoke the runnable with a timeout guard."""
        result = self.runnable.invoke(state, config)
        return {"messages": result}

    def _sleep_backoff(self, attempt: int) -> None:
        """Exponential backoff: 1s, 2s, 4s, ..."""
        delay = 2 ** (attempt - 1)
        logger.debug("Backoff %.1fs before retry", delay)
        time.sleep(delay)

    def _enrich_state_for_retry(self, state: dict, hint: str) -> dict:
        """Add a user message to prod the LLM to produce valid output."""
        messages = list(state.get("messages", []))
        messages.append(("user", hint))
        return {**state, "messages": messages}

    def _build_rejection(self, reason: str) -> dict:
        """Build a response when guardrail rejects the input."""
        from langchain_core.messages import AIMessage

        return {
            "messages": [
                AIMessage(
                    content=f"Request rejected: {reason}",
                )
            ]
        }

    def _build_error_response(self, error_msg: str) -> dict:
        """Build a fallback error response."""
        from langchain_core.messages import AIMessage

        return {
            "messages": [
                AIMessage(
                    content="Sorry, the system encountered an issue processing your request. Please try again later.",
                )
            ]
        }
