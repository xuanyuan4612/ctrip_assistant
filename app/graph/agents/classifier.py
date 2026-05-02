"""
classifier.py - IntentClassifier

Uses a cheap/fast LLM (settings.CLASSIFIER_MODEL, e.g. Haiku or Flash)
to classify user intent into one of 6 categories.

Returns a structured dict: {intent, confidence, entities}

Intents:
  - flight          -  flight search, booking, cancellation, changes
  - hotel           -  hotel search, booking, modification, cancellation
  - car_rental      -  car rental search, booking, modification, cancellation
  - excursion       -  excursion/trip recommendations, booking, cancellation
  - multi_domain    -  user request spans multiple domains
  - clarification   -  greeting, chitchat, unclear, needs more info
"""

import json
import logging
import re
from typing import Optional

from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import RunnableConfig
from langchain_openai import ChatOpenAI

from config import settings

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Intent classification prompt
# ---------------------------------------------------------------------------

CLASSIFIER_SYSTEM_PROMPT = (
    "You are a travel assistant intent classifier. Analyze the user's latest message and determine their intent.\n\n"
    "Available intent categories:\n"
    "1. flight - Flight search, booking, change, cancellation, or any flight/ticket related questions\n"
    "2. hotel - Hotel search, booking, modification, cancellation\n"
    "3. car_rental - Car rental search, booking, modification, cancellation\n"
    "4. excursion - Trip recommendations, sightseeing, local activity booking\n"
    "5. multi_domain - User request spans multiple domains (e.g. book flight + hotel)\n"
    "6. clarification - Greeting, chitchat, unclear intent, needs more information\n\n"
    "Return JSON only, no other content:\n"
    '{{"intent": "<intent_name>", "confidence": <0.0-1.0>, "entities": {{"key": "value"}}}}\n\n'
    "For clarification intent, entities can include \"greeting\": true if user is just saying hello.\n\n"
    "Key entities to extract:\n"
    "- For flight: departure, arrival, date, ticket_no\n"
    "- For hotel: location, checkin_date, checkout_date\n"
    "- For car_rental: location, start_date, end_date\n"
    "- For excursion: location, keywords"
)

CLASSIFIER_HUMAN_TEMPLATE = (
    "User message: {input}\n\n"
    "Conversation history summary (last 3 turns):\n{history_summary}"
)


# ---------------------------------------------------------------------------
# IntentClassifier
# ---------------------------------------------------------------------------

class IntentClassifier:
    """
    Lightweight intent classifier using a cheap LLM (e.g. Haiku, Flash).

    Usage::

        classifier = IntentClassifier()
        result = classifier.classify("I want to book a flight to Beijing")
        # => {"intent": "flight", "confidence": 0.95, "entities": {"arrival": "Beijing"}}

    The classifier can also be used as a LangGraph node:
        node = classifier.as_node()
    """

    SUPPORTED_INTENTS = frozenset({
        "flight",
        "hotel",
        "car_rental",
        "excursion",
        "multi_domain",
        "clarification",
    })

    def __init__(
        self,
        model: Optional[str] = None,
        api_base: Optional[str] = None,
        api_key: Optional[str] = None,
        temperature: float = 0.0,
    ):
        """
        Args:
            model: Model name, defaults to settings.CLASSIFIER_MODEL or "gpt-4o-mini"
            api_base: Custom API base URL
            api_key: API key
            temperature: Sampling temperature (default 0.0 for deterministic)
        """
        self._model_name = model or getattr(settings, "CLASSIFIER_MODEL", "gpt-4o-mini")

        self._llm = ChatOpenAI(
            temperature=temperature,
            model=self._model_name,
            openai_api_key=api_key or getattr(settings, "OPENAI_API_KEY", ""),
            openai_api_base=api_base or getattr(settings, "OPENAI_API_BASE", ""),
        )

        self._prompt = ChatPromptTemplate.from_messages([
            ("system", CLASSIFIER_SYSTEM_PROMPT),
            ("human", CLASSIFIER_HUMAN_TEMPLATE),
        ])

        self._chain = self._prompt | self._llm

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def classify(
        self,
        user_input: str,
        history_summary: str = "",
        config: Optional[RunnableConfig] = None,
    ) -> dict:
        """
        Classify user intent.

        Returns:
            dict with keys: intent, confidence, entities
        """
        try:
            response = self._chain.invoke(
                {"input": user_input, "history_summary": history_summary or "No history"},
                config=config,
            )
            return self._parse_response(response.content)
        except Exception as exc:
            logger.error("Intent classification failed: %s", exc)
            return {
                "intent": "clarification",
                "confidence": 0.0,
                "entities": {},
                "_error": str(exc),
            }

    async def aclassify(
        self,
        user_input: str,
        history_summary: str = "",
        config: Optional[RunnableConfig] = None,
    ) -> dict:
        """Async version of classify."""
        try:
            response = await self._chain.ainvoke(
                {"input": user_input, "history_summary": history_summary or "No history"},
                config=config,
            )
            return self._parse_response(response.content)
        except Exception as exc:
            logger.error("Async intent classification failed: %s", exc)
            return {
                "intent": "clarification",
                "confidence": 0.0,
                "entities": {},
                "_error": str(exc),
            }

    def as_node(self):
        """
        Return a callable suitable for use as a LangGraph node.
        Signature: (state: dict, config: RunnableConfig) -> dict
        """
        def classifier_node(state: dict, config: RunnableConfig) -> dict:
            messages = state.get("messages", [])
            # Get the last user message
            user_input = ""
            history_lines = []
            for msg in messages:
                if hasattr(msg, "type") and msg.type == "human":
                    user_input = msg.content
                else:
                    history_lines.append(
                        f"{getattr(msg, 'type', 'unknown')}: {getattr(msg, 'content', '')}"
                    )

            history_summary = "\n".join(history_lines[-6:])  # last 3 turns (user+ai)
            result = self.classify(user_input, history_summary, config)
            return {"intent_classification": result}

        return classifier_node

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _parse_response(self, content: str) -> dict:
        """Parse LLM JSON response into structured dict."""
        # Try to extract JSON from markdown fences
        json_match = re.search(r"`(?:json)?\s*(\{.*?\})\s*`", content, re.DOTALL)
        if json_match:
            content = json_match.group(1)

        try:
            data = json.loads(content)
        except json.JSONDecodeError:
            # Fallback: try to find {...} in the string
            brace_match = re.search(r"\{[^{}]*\}", content, re.DOTALL)
            if brace_match:
                try:
                    data = json.loads(brace_match.group(0))
                except json.JSONDecodeError:
                    return self._fallback_parse(content)
            else:
                return self._fallback_parse(content)

        intent = data.get("intent", "clarification")
        if intent not in self.SUPPORTED_INTENTS:
            logger.warning("Unknown intent '%s', falling back to clarification", intent)
            intent = "clarification"

        return {
            "intent": intent,
            "confidence": float(data.get("confidence", 0.5)),
            "entities": data.get("entities", {}),
        }

    def _fallback_parse(self, content: str) -> dict:
        """Keyword-based fallback when JSON parsing fails."""
        content_lower = content.lower()
        intent = "clarification"

        if any(kw in content_lower for kw in ["flight", "flight", "ticket", "plane"]):
            intent = "flight"
        elif any(kw in content_lower for kw in ["hotel", "lodging", "accommodation"]):
            intent = "hotel"
        elif any(kw in content_lower for kw in ["car rental", "rental car", "car_rental"]):
            intent = "car_rental"
        elif any(kw in content_lower for kw in ["excursion", "tour", "trip recommendation", "attraction", "activity"]):
            intent = "excursion"

        return {
            "intent": intent,
            "confidence": 0.5,
            "entities": {},
            "_fallback": True,
        }
