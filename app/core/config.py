"""应用配置 (pydantic-settings)"""
from typing import List

from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
    )

    # ── 应用 ──
    APP_NAME: str = "ctrip_assistant"
    DEBUG: bool = False
    HOST: str = "0.0.0.0"
    PORT: int = 8000

    # ── 数据库 ──
    DATABASE_URL: str = Field(..., description="MySQL DSN for business data")
    PG_DATABASE_URL: str = Field(default="", description="PostgreSQL DSN for LangGraph checkpoint/store")

    # ── Redis ──
    REDIS_URL: str = "redis://localhost:6379/0"

    # ── JWT ──
    JWT_SECRET_KEY: SecretStr = Field(..., description="JWT signing secret (64-char hex)")
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # ── CORS ──
    CORS_ORIGINS: List[str] = ["http://localhost:8080"]

    # ── LLM ──
    LLM_PROVIDER: str = "deepseek"
    LLM_MODEL: str = "deepseek-chat"
    LLM_API_KEY: SecretStr = Field(..., description="LLM API key")
    LLM_API_BASE: str = "https://api.deepseek.com/v1"
    LLM_TEMPERATURE: float = 0.8
    LLM_MAX_RETRIES: int = 3
    LLM_TIMEOUT: int = 60

    # ── LLM - 备选 Provider ──
    LLM_PROVIDER_BACKUP: str = "openai"
    LLM_MODEL_BACKUP: str = "gpt-4o"
    LLM_API_KEY_BACKUP: SecretStr = Field(default=SecretStr(""), description="Backup LLM API key")
    LLM_API_BASE_BACKUP: str = "https://api.openai.com/v1"

    # ── 意图分类器 (低成本模型) ──
    CLASSIFIER_MODEL: str = "deepseek-chat"
    CLASSIFIER_TEMPERATURE: float = 0.0
    CLASSIFIER_CONFIDENCE_THRESHOLD: float = 0.85

    # ── Embedding ──
    EMBEDDING_API_KEY: SecretStr = Field(default=SecretStr(""), description="Embedding API key")
    EMBEDDING_API_BASE: str = "https://api.deepseek.com/v1"
    EMBEDDING_MODEL: str = "text-embedding-3-small"
    EMBEDDING_DIMENSIONS: int = 768

    # ── Qdrant ──
    QDRANT_URL: str = "http://localhost:6333"
    QDRANT_COLLECTION: str = "travel_faq"

    # ── 速率限制 ──
    RATE_LIMIT_LOGIN: str = "5/minute"
    RATE_LIMIT_GLOBAL: str = "100/minute"

    # ── 白名单 ──
    AUTH_WHITELIST: List[str] = [
        "/api/v1/auth/login",
        "/api/v1/auth/register",
        "/api/v1/health",
        "/docs",
        "/openapi.json",
    ]

    # ── 日志 ──
    LOG_LEVEL: str = "INFO"
    LOG_FORMAT: str = "json"  # json | console

    # ── Token 预算 ──
    TOKEN_BUDGET_PER_USER_DAY: int = 100_000
    TOKEN_BUDGET_PER_SESSION: int = 50_000


settings = Settings()
