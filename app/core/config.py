# -*- coding: utf-8 -*-
"""
应用配置模块（基于 pydantic-settings）

本模块是整个应用的配置中心。所有环境变量通过 .env 文件加载，
由 pydantic-settings 自动校验类型并提供 IDE 提示。

设计原则：
  - 所有配置集中管理，避免散落在各模块中
  - 敏感字段（密钥、API Key）使用 SecretStr 类型，防止日志泄露
  - 提供合理的默认值，降低本地开发配置成本
  - WHY：统一配置入口方便运维管理，SecretStr 防止误打印密钥
"""
from typing import List

from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """
    全局配置类

    继承自 pydantic-settings 的 BaseSettings，支持从环境变量、.env 文件
    自动读取配置。所有字段均带类型注解，pydantic 会在启动时校验类型。

    使用方式：
        from app.core.config import settings
        settings.DATABASE_URL  # 直接访问字段
    """

    # ── pydantic 配置元数据 ──
    # 指定 .env 文件路径和编码，开启大小写敏感（默认小写化字段名）
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
    )

    # ══════════════════════════════════════════
    #  应用基础配置
    # ══════════════════════════════════════════
    APP_NAME: str = "ctrip_assistant"  # 应用名称，用于日志和监控标记
    DEBUG: bool = False                # 调试模式开关：开启后输出更详细日志、使用 ConsoleFormatter
    HOST: str = "0.0.0.0"             # 监听地址，0.0.0.0 表示监听所有网络接口
    PORT: int = 8000                   # 服务端口

    # ══════════════════════════════════════════
    #  数据库连接
    # ══════════════════════════════════════════
    # MySQL DSN：存储用户、订单等业务数据
    # 格式：mysql+pymysql://user:pass@host:port/db
    DATABASE_URL: str = Field(..., description="MySQL DSN for business data")
    # PostgreSQL DSN：存储 LangGraph Agent 的记忆（checkpoint + store）
    # 可选配置，为空时使用 SQLite 本地替代
    PG_DATABASE_URL: str = Field(default="", description="PostgreSQL DSN for LangGraph checkpoint/store")

    # ══════════════════════════════════════════
    #  Redis（缓存/限流/会话）
    # ══════════════════════════════════════════
    # Redis 连接字符串，用于速率限制和会话缓存
    REDIS_URL: str = "redis://localhost:6379/0"

    # ══════════════════════════════════════════
    #  JWT（认证令牌）
    # ══════════════════════════════════════════
    # JWT 签名密钥：应使用 secrets.token_hex(32) 生成
    # SecretStr 类型确保 repr() 时不会泄露密钥值
    JWT_SECRET_KEY: SecretStr = Field(..., description="JWT signing secret (64-char hex)")
    JWT_ALGORITHM: str = "HS256"                # JWT 签名算法，HS256 = HMAC-SHA256
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30        # 访问令牌过期时间（短时效，减少泄露风险）
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7           # 刷新令牌过期时间（长时效，方便续期）

    # ══════════════════════════════════════════
    #  CORS（跨域资源共享）
    # ══════════════════════════════════════════
    # 允许跨域请求的前端来源列表
    # 生产环境应替换为实际前端域名
    CORS_ORIGINS: List[str] = ["http://localhost:8080"]

    # ══════════════════════════════════════════
    #  LLM（主模型配置）
    # ══════════════════════════════════════════
    LLM_PROVIDER: str = "deepseek"            # LLM 供应商，当前支持 deepseek / openai
    LLM_MODEL: str = "deepseek-chat"          # 模型名称
    LLM_API_KEY: SecretStr = Field(..., description="LLM API key")  # API 密钥
    LLM_API_BASE: str = "https://api.deepseek.com/v1"  # API 端点地址
    LLM_TEMPERATURE: float = 0.8              # 生成温度：越高输出越随机，越低越确定
    LLM_MAX_RETRIES: int = 3                  # API 调用失败重试次数
    LLM_TIMEOUT: int = 60                     # API 调用超时时间（秒）

    # ══════════════════════════════════════════
    #  LLM - 备选 Provider（容灾降级）
    # ══════════════════════════════════════════
    # 当主 Provider 不可用时自动切换，保证服务高可用
    LLM_PROVIDER_BACKUP: str = "openai"       # 备选供应商
    LLM_MODEL_BACKUP: str = "gpt-4o"          # 备选模型
    LLM_API_KEY_BACKUP: SecretStr = Field(default=SecretStr(""), description="Backup LLM API key")
    LLM_API_BASE_BACKUP: str = "https://api.openai.com/v1"

    # ══════════════════════════════════════════
    #  意图分类器（低成本模型）
    # ══════════════════════════════════════════
    # 使用更小/更便宜的模型做意图识别，降低每次对话的成本
    CLASSIFIER_MODEL: str = "deepseek-chat"          # 分类器模型
    CLASSIFIER_TEMPERATURE: float = 0.0              # 温度为 0 保证分类结果确定性
    CLASSIFIER_CONFIDENCE_THRESHOLD: float = 0.85    # 置信度阈值，低于此值回退到主模型

    # ══════════════════════════════════════════
    #  Embedding（向量化）
    # ══════════════════════════════════════════
    # 用于 RAG 检索的文本向量化配置
    EMBEDDING_API_KEY: SecretStr = Field(default=SecretStr(""), description="Embedding API key")
    EMBEDDING_API_BASE: str = "https://api.deepseek.com/v1"
    EMBEDDING_MODEL: str = "text-embedding-3-small"  # 向量化模型
    EMBEDDING_DIMENSIONS: int = 768                  # 向量维度，影响检索精度和存储

    # ══════════════════════════════════════════
    #  Qdrant（向量数据库）
    # ══════════════════════════════════════════
    QDRANT_URL: str = "http://localhost:6333"    # Qdrant 服务地址
    QDRANT_COLLECTION: str = "travel_faq"        # 存储 FAQ 向量的集合名称

    # ══════════════════════════════════════════
    #  速率限制
    # ══════════════════════════════════════════
    # 使用 slowapi 进行速率限制，格式遵循："[count]/[window]"
    RATE_LIMIT_LOGIN: str = "5/minute"    # 登录接口：每分钟最多 5 次，防暴力破解
    RATE_LIMIT_GLOBAL: str = "100/minute" # 全局接口：每分钟最多 100 次，防滥用

    # ══════════════════════════════════════════
    #  认证白名单
    # ══════════════════════════════════════════
    # 这些路径不需要 JWT 令牌即可访问
    # WHY：登录/注册/健康检查/Swagger 文档必须在未认证状态下可访问
    AUTH_WHITELIST: List[str] = [
        "/api/v1/auth/login",      # 登录端点
        "/api/v1/auth/register",   # 注册端点
        "/api/v1/health",          # 健康检查
        "/docs",                   # Swagger UI 文档
        "/openapi.json",           # OpenAPI 规范文件
    ]

    # ══════════════════════════════════════════
    #  日志配置
    # ══════════════════════════════════════════
    LOG_LEVEL: str = "INFO"           # 日志级别：DEBUG / INFO / WARNING / ERROR
    LOG_FORMAT: str = "json"          # 日志格式：json（生产环境，适合日志平台收集）或 console（开发环境，可读性强）

    # ══════════════════════════════════════════
    #  Token 预算（成本控制）
    # ══════════════════════════════════════════
    # 限制 LLM API 的调用开销，防止单个用户超额消费
    TOKEN_BUDGET_PER_USER_DAY: int = 100_000     # 单用户每日 Token 上限
    TOKEN_BUDGET_PER_SESSION: int = 50_000        # 单次会话 Token 上限


# 全局单例：导入即加载配置，各模块共享同一个实例
# WHY：保证配置只加载一次，避免重复读取 .env 文件
settings = Settings()
