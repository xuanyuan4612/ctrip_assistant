"""DeepSeek LLM Provider"""
from langchain_openai import ChatOpenAI

from app.core.config import settings
from app.infrastructure.llm.base import LLMProviderFactory
from app.infrastructure.llm.openai import OpenAIProvider


class DeepSeekProvider(OpenAIProvider):
    def __init__(self):
        super().__init__(
            api_key=settings.LLM_API_KEY_BACKUP.get_secret_value() or settings.LLM_API_KEY.get_secret_value(),
            api_base=settings.LLM_API_BASE_BACKUP,
            model=settings.LLM_MODEL_BACKUP,
        )


LLMProviderFactory.register("deepseek", DeepSeekProvider)
