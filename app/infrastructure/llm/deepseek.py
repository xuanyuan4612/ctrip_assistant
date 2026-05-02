"""DeepSeek LLM Provider (默认)"""
from langchain_openai import ChatOpenAI

from app.core.config import settings
from app.infrastructure.llm.base import LLMProviderFactory
from app.infrastructure.llm.openai import OpenAIProvider


class DeepSeekProvider(OpenAIProvider):
    def __init__(self):
        super().__init__(
            api_key=settings.LLM_API_KEY.get_secret_value(),
            api_base=settings.LLM_API_BASE,
            model=settings.LLM_MODEL,
        )


LLMProviderFactory.register("deepseek", DeepSeekProvider)
