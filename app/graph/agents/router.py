"""
router.py - ModelRouter

Complexity-based model selection using 8 heuristic signals.
Routes to cheap (70%) / medium (25%) / expensive (5%) models.

Signals considered:
  1. Message count         -  conversational turns so far
  2. Token count (est.)    -  rough estimate from message lengths
  3. Domain count          -  number of distinct domains mentioned
  4. Tool call depth       -  how many nested tool calls in history
  5. Ambiguity markers     -  vague terms, pronouns, missing params
  6. Language switching    -  code-switching between languages
  7. Emotional sentiment   -  frustration, urgency markers
  8. Multi-intent pattern  -  AND/also/plus connectors between domains
"""

import logging
import re
from typing import Optional

from config import settings

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Complexity tier constants
# ---------------------------------------------------------------------------

TIER_CHEAP = "cheap"           # 70% - fast/cheap model (Haiku, Flash, Qwen-7B)
TIER_MEDIUM = "medium"         # 25% - balanced model (GPT-4o-mini, Qwen-14B)
TIER_EXPENSIVE = "expensive"   # 5% - best model (GPT-4o, Claude 3.5 Sonnet)

DOMAIN_KEYWORDS = {
    "flight": ["flight", "flight", "ticket", "boarding", "plane"],
    "hotel": ["hotel", "lodging", "accommodation", "check-in", "checkin"],
    "car_rental": ["car rental", "rental car", "car_rental"],
    "excursion": [
        "excursion", "tour", "trip recommendation", "attraction", "activity",
    ],
}

AMBIGUITY_MARKERS = [
    r"\b(some|any|that|what)\b",
    r"\b(I don'?t know|not sure|unknown)\b",
    r"\b(whatever|either way)\b",
]

URGENCY_MARKERS = [
    r"\b(urgent|asap|quick|immediately)\b",
    r"\b(frustrated|angry|disappointed)\b",
    r"\b(complaint)\b",
]

MULTI_INTENT_CONNECTORS = [
    r"\b(and\s+also|plus|as\s+well)\b",
    r"\b(and)\b.*\b(and)\b",
]


# ---------------------------------------------------------------------------
# ModelRouter
# ---------------------------------------------------------------------------

class ModelRouter:
    """
    Routes requests to the appropriate model tier based on complexity.

    Usage::

        router = ModelRouter()
        tier = router.route(state)
        # => "cheap", "medium", or "expensive"

        # Get a configured LLM for a given state:
        llm = router.select_llm(state)
    """

    def __init__(
        self,
        cheap_model: str = "",
        cheap_base_url: str = "",
        medium_model: str = "",
        expensive_model: str = "",
    ):
        self.cheap_model = cheap_model or getattr(settings, "CHEAP_MODEL", "Qwen-7B")
        self.cheap_base_url = cheap_base_url or getattr(settings, "CHEAP_BASE_URL", "http://localhost:6006/v1")
        self.medium_model = medium_model or getattr(settings, "MEDIUM_MODEL", "gpt-4o-mini")
        self.expensive_model = expensive_model or getattr(settings, "EXPENSIVE_MODEL", "gpt-4o")

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def route(self, state: dict) -> str:
        """
        Classify complexity tier based on heuristic signals.

        Returns one of: "cheap", "medium", "expensive"
        """
        score = self._compute_complexity_score(state)
        return self._score_to_tier(score)

    def select_llm(self, state: dict):
        """
        Return a configured ChatOpenAI instance for the appropriate tier.

        Usage::

            router = ModelRouter()
            llm = router.select_llm(state)
            result = llm.invoke(...)
        """
        from langchain_openai import ChatOpenAI

        tier = self.route(state)
        if tier == TIER_CHEAP:
            return ChatOpenAI(
                temperature=0.8,
                model=self.cheap_model,
                openai_api_key="EMPTY",
                openai_api_base=self.cheap_base_url,
            )
        elif tier == TIER_MEDIUM:
            return ChatOpenAI(
                temperature=0.3,
                model=self.medium_model,
                openai_api_key=getattr(settings, "OPENAI_API_KEY", ""),
                openai_api_base=getattr(settings, "OPENAI_API_BASE", ""),
            )
        else:  # expensive
            return ChatOpenAI(
                temperature=0.1,
                model=self.expensive_model,
                openai_api_key=getattr(settings, "OPENAI_API_KEY", ""),
                openai_api_base=getattr(settings, "OPENAI_API_BASE", ""),
            )

    def as_node(self):
        """
        Return a callable suitable for use as a LangGraph node.
        Sets 'model_tier' in state.
        """
        def router_node(state: dict, config=None) -> dict:
            tier = self.route(state)
            return {"model_tier": tier}

        return router_node

    # ------------------------------------------------------------------
    # Complexity scoring
    # ------------------------------------------------------------------

    def _compute_complexity_score(self, state: dict) -> float:
        """
        Compute a complexity score in [0.0, 1.0].

        Each of the 8 signals contributes to the final score.
        Higher score = more complex = more expensive model needed.
        """
        messages = state.get("messages", [])
        if not messages:
            return 0.0

        scores = []

        # 1. Message count (0-0.15)
        msg_count = len(messages)
        scores.append(min(msg_count / 20.0, 1.0) * 0.15)

        # 2. Estimated token count (0-0.15)
        total_chars = sum(len(str(m.content)) for m in messages if hasattr(m, "content"))
        est_tokens = total_chars / 2.0  # rough: ~2 chars per CJK token
        scores.append(min(est_tokens / 2000.0, 1.0) * 0.15)

        # 3. Domain count (0-0.15)
        domain_count = self._count_domains(messages)
        scores.append(min(domain_count / 4.0, 1.0) * 0.15)

        # 4. Tool call depth (0-0.10)
        tool_depth = self._estimate_tool_depth(messages)
        scores.append(min(tool_depth / 5.0, 1.0) * 0.10)

        # 5. Ambiguity markers (0-0.10)
        last_human = self._get_last_human_message(messages)
        if last_human:
            ambig_score = min(
                sum(1 for pat in AMBIGUITY_MARKERS if re.search(pat, str(last_human))) / 3.0,
                1.0,
            )
            scores.append(ambig_score * 0.10)
        else:
            scores.append(0.0)

        # 6. Language switching (0-0.10)
        lang_switch = self._detect_language_switching(messages)
        scores.append(min(lang_switch, 1.0) * 0.10)

        # 7. Emotional sentiment / urgency (0-0.10)
        all_text = " ".join(str(m.content) for m in messages if hasattr(m, "content"))
        urgency = min(
            sum(1 for pat in URGENCY_MARKERS if re.search(pat, all_text)) / 3.0,
            1.0,
        )
        scores.append(urgency * 0.10)

        # 8. Multi-intent pattern (0-0.10)
        multi = 1.0 if self._detect_multi_intent(messages) else 0.0
        scores.append(multi * 0.10)

        total = sum(scores)
        logger.debug(
            "Complexity score: %.3f (signals: msg_cnt=%.3f tokens=%.3f "
            "domains=%.3f tools=%.3f ambig=%.3f lang=%.3f urgency=%.3f multi=%.3f)",
            total,
            min(msg_count / 20.0, 1.0) * 0.15,
            min(est_tokens / 2000.0, 1.0) * 0.15,
            min(domain_count / 4.0, 1.0) * 0.15,
            min(tool_depth / 5.0, 1.0) * 0.10,
            scores[4] if len(scores) > 4 else 0,
            scores[5] if len(scores) > 5 else 0,
            scores[6] if len(scores) > 6 else 0,
            scores[7] if len(scores) > 7 else 0,
        )

        return total

    def _score_to_tier(self, score: float) -> str:
        """
        Map complexity score to model tier.

        Target distribution: cheap ~70%, medium ~25%, expensive ~5%

        Thresholds:
          0.00 - 0.40  ->  cheap
          0.40 - 0.70  ->  medium
          0.70 - 1.00  ->  expensive
        """
        if score >= 0.70:
            return TIER_EXPENSIVE
        elif score >= 0.40:
            return TIER_MEDIUM
        return TIER_CHEAP

    # ------------------------------------------------------------------
    # Signal helpers
    # ------------------------------------------------------------------

    def _count_domains(self, messages: list) -> int:
        """Count how many distinct domains are mentioned across all messages."""
        all_text = " ".join(
            str(m.content).lower() for m in messages if hasattr(m, "content")
        )
        domains_found = set()
        for domain, keywords in DOMAIN_KEYWORDS.items():
            if any(kw in all_text for kw in keywords):
                domains_found.add(domain)
        return len(domains_found)

    def _estimate_tool_depth(self, messages: list) -> int:
        """Estimate tool call nesting depth from tool_call_ids in messages."""
        depth = 0
        for m in messages:
            if hasattr(m, "tool_calls") and m.tool_calls:
                depth += len(m.tool_calls)
            if hasattr(m, "tool_call_id") and m.tool_call_id:
                depth += 1
        return depth

    def _get_last_human_message(self, messages: list) -> str:
        """Get the content of the last human message."""
        for m in reversed(messages):
            if hasattr(m, "type") and m.type == "human":
                return str(m.content)
            if isinstance(m, tuple) and len(m) >= 2 and m[0] == "user":
                return str(m[1])
        return ""

    def _detect_language_switching(self, messages: list) -> float:
        """
        Detect code-switching between Chinese and English.
        Returns 0.0 (no switching) to 1.0 (heavy switching).
        """
        cjk = re.compile(r"[\u4e00-\u9fff\u3000-\u303f\uff00-\uffef]")
        latin = re.compile(r"[a-zA-Z]{2,}")

        switches = 0
        segments = 0
        prev_lang = None

        for m in messages:
            text = str(m.content) if hasattr(m, "content") else ""
            has_cjk = bool(cjk.search(text))
            has_latin = bool(latin.search(text))

            if has_cjk and has_latin:
                segments += 1
                current = "mixed"
            elif has_cjk:
                current = "zh"
            elif has_latin:
                current = "en"
            else:
                continue

            if prev_lang is not None and current != prev_lang:
                switches += 1
            prev_lang = current

        if segments == 0:
            return 0.0
        return min(switches / segments, 1.0)

    def _detect_multi_intent(self, messages: list) -> bool:
        """Check if the last human message contains multi-intent connectors."""
        last_human = self._get_last_human_message(messages)
        if not last_human:
            return False
        text = str(last_human).lower()
        return any(re.search(pat, text) for pat in MULTI_INTENT_CONNECTORS)


# ---------------------------------------------------------------------------
# Singleton default
# ---------------------------------------------------------------------------

default_router = ModelRouter()
