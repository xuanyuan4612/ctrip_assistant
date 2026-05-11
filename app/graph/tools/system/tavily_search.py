"""Tavily web search tool for the primary agent.

Provides internet search capabilities through Tavily API.
"""

from __future__ import annotations

from langchain_community.tools.tavily_search import TavilySearchResults

from app.core.config import settings

tavily_tool = TavilySearchResults(
    max_results=1,
    tavily_api_key=settings.TAVILY_API_KEY.get_secret_value()
    if hasattr(settings, "TAVILY_API_KEY")
    else "",
)

__all__ = ["tavily_tool"]
