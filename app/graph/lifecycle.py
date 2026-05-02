"""
lifecycle.py - Session Lifecycle Management

Handles the beginning and end of a conversational session.
Exports:
    load_user_memory(state, config) -> dict
    load_user_info(state) -> dict
    extract_memories(state, config) -> dict
    summarize(state, config) -> dict
    SummarizationNode (alias for summarize)
"""

from __future__ import annotations
import logging
from typing import Any, Dict
from langchain_core.runnables import RunnableConfig

logger = logging.getLogger(__name__)


def load_user_info(state: dict) -> dict:
    """Load the current user's flight/passenger information.

    Invokes fetch_user_flight_information and stores result in user_info.
    Returns empty dict on failure rather than crashing the graph.
    """
    try:
        from tools.flights_tools import fetch_user_flight_information
        user_info = fetch_user_flight_information.invoke({})
        logger.info("Loaded user info: %d record(s)",
                     len(user_info) if isinstance(user_info, list) else 1)
        return {"user_info": user_info}
    except Exception as exc:
        logger.warning("load_user_info failed: %s", exc)
        return {"user_info": {}}


def load_user_memory(state: dict, config: RunnableConfig) -> dict:
    """Extended session-start loader that also hydrates user_id/username."""
    result: Dict[str, Any] = {}

    try:
        from tools.flights_tools import fetch_user_flight_information
        user_info = fetch_user_flight_information.invoke({})
        result["user_info"] = user_info
    except Exception as exc:
        logger.warning("load_user_memory (flight info): %s", exc)
        result["user_info"] = {}

    cfg = config.get("configurable", {})
    user_id = cfg.get("user_id")
    username = cfg.get("username")
    if user_id is not None:
        result["user_id"] = user_id
    if username is not None:
        result["username"] = username

    logger.info("load_user_memory: user_id=%s username=%s",
                result.get("user_id", "N/A"), result.get("username", "N/A"))
    return result


def extract_memories(state: dict, config: RunnableConfig) -> dict:
    """Extract and persist key memories from the completed conversation.

    Currently a no-op placeholder that logs conversation length.
    Future: call LLM to produce summary, persist to vector store.
    """
    messages = state.get("messages", [])
    logger.info("extract_memories: %d messages in conversation", len(messages))
    return {"_memory_extracted": True}


def summarize(state: dict, config: RunnableConfig) -> dict:
    """Automatic conversation summarisation placeholder.

    Triggers when token budget is exceeded.
    Currently a no-op; logs estimated tokens.
    """
    messages = state.get("messages", [])
    total_chars = sum(
        len(str(m.content)) for m in messages if hasattr(m, "content")
    )
    est_tokens = total_chars / 2.0
    logger.debug("summarize: %d messages, ~%d estimated tokens",
                 len(messages), int(est_tokens))
    return {}


SummarizationNode = summarize
