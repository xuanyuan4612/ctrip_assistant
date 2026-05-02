"""LLM Provider 抽象基类"""
from abc import ABC, abstractmethod

from langchain_core.language_models import BaseChatModel
from langchain_core.embeddings import Embeddings


class AbstractLLMProvider(ABC):
    @abstractmethod
    def get_chat_model(self, **kwargs) -> BaseChatModel:
        ...

    @abstractmethod
    def get_embedding_model(self) -> Embeddings:
        ...

    @abstractmethod
    def health_check(self) -> bool:
        ...


class LLMProviderFactory:
    """LLM Provider 工厂"""

    _providers: dict = {}

    @classmethod
    def register(cls, name: str, provider_class):
        cls._providers[name] = provider_class

    @classmethod
    def create(cls, name: str, **kwargs) -> AbstractLLMProvider:
        if name not in cls._providers:
            raise ValueError(f"Unknown LLM provider: {name}. Available: {list(cls._providers.keys())}")
        return cls._providers[name](**kwargs)
