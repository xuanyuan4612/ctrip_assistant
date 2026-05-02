"""OpenAI-compatible LLM Provider (used as fallback)"""
from langchain_core.language_models import BaseChatModel
from langchain_core.embeddings import Embeddings
from langchain_openai import ChatOpenAI, OpenAIEmbeddings

from app.core.config import settings
from app.infrastructure.llm.base import AbstractLLMProvider, LLMProviderFactory


class OpenAIProvider(AbstractLLMProvider):
    def __init__(self, api_key: str = None, api_base: str = None, model: str = None):
        self.api_key = api_key or settings.LLM_API_KEY_BACKUP.get_secret_value() or settings.LLM_API_KEY.get_secret_value()
        self.api_base = api_base or settings.LLM_API_BASE_BACKUP
        self.model = model or settings.LLM_MODEL_BACKUP

    def get_chat_model(self, **kwargs) -> BaseChatModel:
        return ChatOpenAI(
            model=kwargs.get("model", self.model),
            api_key=kwargs.get("api_key", self.api_key),
            base_url=kwargs.get("base_url", self.api_base),
            temperature=kwargs.get("temperature", settings.LLM_TEMPERATURE),
            max_retries=kwargs.get("max_retries", settings.LLM_MAX_RETRIES),
            timeout=kwargs.get("timeout", settings.LLM_TIMEOUT),
        )

    def get_embedding_model(self) -> Embeddings:
        return OpenAIEmbeddings(
            api_key=settings.EMBEDDING_API_KEY.get_secret_value() or self.api_key,
            base_url=settings.EMBEDDING_API_BASE or self.api_base,
            model=settings.EMBEDDING_MODEL,
            dimensions=settings.EMBEDDING_DIMENSIONS,
        )

    def health_check(self) -> bool:
        try:
            model = ChatOpenAI(model=self.model, api_key=self.api_key, base_url=self.api_base, max_tokens=1)
            model.invoke("ping")
            return True
        except Exception:
            return False


LLMProviderFactory.register("openai", OpenAIProvider)
