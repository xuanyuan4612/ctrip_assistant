# 携程 AI 助手 — 生产级升级架构文档

> **版本**: v1.0  
> **日期**: 2026-04-27  
> **目标**: 从研究原型升级为生产级可部署服务  
> **决策依据**: Docker Compose 单机部署 / 云端 LLM / 统一 MySQL / 中规模 (100-1000 并发)

---

## 目录

1. [现状评估](#1-现状评估)
2. [目标架构蓝图](#2-目标架构蓝图)
3. [详细升级计划](#3-详细升级计划)
   - [3.1 项目结构重组](#31-项目结构重组)
   - [3.2 配置管理升级](#32-配置管理升级)
   - [3.3 数据层升级](#33-数据层升级)
   - [3.4 API 与安全层升级](#34-api-与安全层升级)
   - [3.5 LLM 与 Agent 系统升级](#35-llm-与-agent-系统升级)
   - [3.6 可观测性升级](#36-可观测性升级)
   - [3.7 测试体系](#37-测试体系)
   - [3.8 部署与运维](#38-部署与运维)
4. [迁移路线图](#4-迁移路线图)
5. [待确认问题](#5-待确认问题)

---

## 1. 现状评估

### 1.1 项目概览

| 维度 | 当前状态 |
|------|----------|
| **定位** | 携程瑞士航空 AI 助手（多智能体对话系统） |
| **入口** | FastAPI REST API + Gradio 交互测试 UI |
| **LLM** | 本地 Qwen-7B + 多个云端 LLM（注释中） |
| **数据库** | SQLite（业务数据）+ MySQL（用户认证），双数据库 |
| **Agent 框架** | LangGraph StateGraph，多智能体 Supervisor 模式 |
| **配置** | Dynaconf，仅 development.yml 有内容 |
| **测试** | **零覆盖** |
| **部署** | 裸 Python 进程 (`python main.py`) |

### 1.2 关键问题清单

#### 🔴 阻断级 (P0)

| # | 问题 | 位置 | 影响 |
|---|------|------|------|
| 1 | **JWT 密钥公开** — 使用 FastAPI 官方教程示例密钥 | `config/development.yml:15` | 任何人可伪造 JWT 令牌 |
| 2 | **数据库密码明文** — `root:123123` 存储于版本控制 | `config/development.yml:10-11` | 数据库凭据泄露 |
| 3 | **API 密钥硬编码** — Tavily、OpenAI Embedding 密钥在源码中 | `llm_tavily.py:43`, `retriever_vector.py:25` | API 密钥泄露 |
| 4 | **生产配置为空** — `production.yml` 0 字节，环境切换器失效 | `config/__init__.py`, `config/production.yml` | 生产环境回退到开发配置 |
| 5 | **`tools/__init__.py` f-string Bug** — `local_file` 和 `backup_file` 是字面字符串 | `tools/__init__.py:9,12` | `update_dates()` 静默失败 |
| 6 | **`InDBMixin` 导入断裂** — 被注释但被引用 | `api/schemas.py:14-22`, `user_schemas.py:6` | 运行时 `ImportError` |
| 7 | **SQLite 无连接池** — 每次工具调用 `connect(db)` 新建连接 | 所有 `tools/*_tools.py` | 并发下连接泄漏/竞争 |

#### 🟠 高风险 (P1)

| # | 问题 | 位置 |
|---|------|------|
| 8 | `sqlalchemy echo=True` 在生产中记录所有 SQL | `db/__init__.py:19` |
| 9 | 无 LLM 调用重试/退避/超时机制 | `llm_tavily.py`, `assistant.py:39` |
| 10 | 无限重试循环 (`while True`) | `assistant.py:39` |
| 11 | 无速率限制（登录接口暴力破解）| `api/system_mgt/user_views.py:46` |
| 12 | `passenger_id` 硬编码 | `graph_gradio.py:130`, `graph_schemas.py:12` |
| 13 | 白名单 `re.match` 不锚定 — 前缀匹配绕过风险 | `middlewares.py:32`, `docs_oauth2.py:41` |
| 14 | JWT 令牌无黑名单/撤销机制 | `utils/jwt_utils.py` |
| 15 | MemorySaver 检查点不持久化 — 重启丢失所有对话 | `graph_gradio.py:109` |

#### 🟡 中风险 (P2)

| # | 问题 |
|---|------|
| 16 | 3 路图定义重复: `graph_gradio.py` / `finally_graph.py` / `第三个流程图.py` |
| 17 | 子图构建器 76% 重复模板代码 (`build_child_graph.py`) |
| 18 | 3 个历史版本文件为死代码 (`第一个/第二个/第三个流程图.py`) |
| 19 | `api/__init__.py` 含测试垃圾代码 |
| 20 | 提示词模板中 `time=datetime.now()` 在模块导入时固化 |
| 21 | `draw_png.py` 静默吞掉所有异常 |
| 22 | 日志仅控制台，文件日志被注释 |
| 23 | `route_primary_assistant` 抛出 `ValueError("无效的路由")` 使整个会话崩溃 |
| 24 | 无结构化异常体系 — 到处 `raise ValueError` |

---

## 2. 目标架构蓝图

### 2.1 架构决策 (ADR)

| ADR | 决策 | 理由 |
|-----|------|------|
| ADR-1 | **移除 Gradio，仅保留 FastAPI** | 用户确认生产环境不需要 Gradio UI |
| ADR-2 | **切换到云端 LLM** | 性能优于本地 Qwen-7B；通过 Provider 抽象层支持多模型切换 |
| ADR-3 | **统一到 MySQL** | SQLite 不支持并发写入；MySQL 统一管理业务数据+用户认证 |
| ADR-4 | **Docker Compose 单机部署** | 中规模场景足够；简化运维 |
| ADR-5 | **pydantic-settings 替代 Dynaconf** | 类型安全的配置管理，`.env` 支持，与 FastAPI 生态更兼容 |
| ADR-6 | **Poetry 替代裸 pip** | 依赖锁定、虚拟环境管理、确定性构建 |
| ADR-7 | **保留 LangGraph 多智能体架构** | 核心架构合理，升级而非重写 |

### 2.2 目标架构图

```
┌─────────────────────────────────────────────────────────────┐
│                     Docker Compose                           │
│                                                              │
│  ┌──────────────┐   ┌──────────────┐   ┌──────────────┐     │
│  │   Nginx      │──▶│   FastAPI    │──▶│    MySQL     │     │
│  │  (反向代理)  │   │  (App Server)│   │   (8.0)     │     │
│  │  :443/80     │   │  :8000       │   │  :3306      │     │
│  └──────────────┘   └──────┬───────┘   └──────────────┘     │
│                             │                                │
│                    ┌────────┴────────┐                       │
│                    ▼                 ▼                       │
│             ┌─────────────┐   ┌─────────────┐               │
│             │   Redis     │   │  Cloud LLM  │               │
│             │  (缓存/限流) │   │  (API)      │               │
│             │  :6379      │   │  OpenAI/     │               │
│             └─────────────┘   │  DeepSeek   │               │
│                               └─────────────┘               │
│                                                              │
│  ┌──────────────────────────────────────────────────────┐   │
│  │  应用内部架构 (FastAPI)                                │   │
│  │                                                        │   │
│  │  Middleware Stack:                                     │   │
│  │   CORS → RequestID → RateLimit → Auth → Logging →     │   │
│  │                                                        │   │
│  │  ┌──────────────────┐  ┌──────────────────────────┐   │   │
│  │  │  REST API Layer  │  │  Multi-Agent Graph System │   │   │
│  │  │  /api/v1/auth/*  │  │                            │   │   │
│  │  │  /api/v1/users/* │  │  Primary Assistant         │   │   │
│  │  │  /api/v1/graph/* │  │   ├─ Flight Sub-Agent      │   │   │
│  │  │  /api/v1/health  │  │   ├─ Hotel Sub-Agent       │   │   │
│  │  └──────────────────┘  │   ├─ Car Sub-Agent         │   │   │
│  │                         │   └─ Excursion Sub-Agent   │   │   │
│  │  ┌──────────────────┐  │                            │   │   │
│  │  │  Service Layer   │  │  LLM Provider Abstraction  │   │   │
│  │  │  AuthService     │  │   ├─ OpenAI Provider       │   │   │
│  │  │  GraphService    │  │   ├─ DeepSeek Provider     │   │   │
│  │  │  UserService     │  │   └─ (extensible)          │   │   │
│  │  └──────────────────┘  └──────────────────────────┘   │   │
│  │                                                        │   │
│  │  ┌──────────────────────────────────────────────────┐  │   │
│  │  │  Data Access Layer                                │  │   │
│  │  │  Repository Pattern (SQLAlchemy 2.0 async)        │  │   │
│  │  │   ├─ FlightRepository / HotelRepository / ...     │  │   │
│  │  │   ├─ UserRepository                               │  │   │
│  │  │   └─ SessionRepository (conversation state)       │  │   │
│  │  └──────────────────────────────────────────────────┘  │   │
│  └──────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
```

### 2.3 目标项目结构

```
ctrip_assistant/
├── app/                          # FastAPI 应用主包
│   ├── __init__.py
│   ├── main.py                   # 应用工厂 + 生命周期
│   ├── core/                     # 核心基础设施
│   │   ├── __init__.py
│   │   ├── config.py             # pydantic-settings 配置
│   │   ├── security.py           # JWT, 密码哈希
│   │   ├── exceptions.py         # 结构化异常体系
│   │   └── logging.py            # 日志配置
│   ├── middleware/                # 中间件层
│   │   ├── __init__.py
│   │   ├── auth.py               # JWT 认证中间件
│   │   ├── cors.py               # CORS 配置
│   │   ├── rate_limit.py         # 速率限制
│   │   └── request_id.py         # 请求追踪 ID
│   ├── api/                      # API 路由
│   │   ├── __init__.py
│   │   ├── deps.py               # FastAPI 依赖注入
│   │   └── v1/                   # API v1
│   │       ├── __init__.py
│   │       ├── router.py         # 主路由聚合
│   │       ├── auth.py           # POST /auth/login, /auth/register
│   │       ├── users.py          # CRUD /users
│   │       ├── graph.py          # POST /graph (多智能体)
│   │       └── health.py         # GET /health
│   ├── schemas/                  # Pydantic 模型
│   │   ├── __init__.py
│   │   ├── user.py               # 用户 Schema
│   │   ├── graph.py              # Graph 请求/响应 Schema
│   │   └── common.py             # 公共 Schema（分页等）
│   ├── services/                 # 业务服务层
│   │   ├── __init__.py
│   │   ├── auth_service.py       # 认证业务逻辑
│   │   ├── user_service.py       # 用户业务逻辑
│   │   └── graph_service.py      # 多智能体编排服务
│   ├── graph/                    # LangGraph 多智能体系统
│   │   ├── __init__.py
│   │   ├── state.py              # State TypedDict
│   │   ├── graph.py              # 图构建（主图 + 参数化子图工厂）
│   │   ├── agents/               # 各智能体 Prompt + Runnable
│   │   │   ├── __init__.py
│   │   │   ├── primary.py        # 主智能体
│   │   │   ├── flight.py         # 航班智能体
│   │   │   ├── hotel.py          # 酒店智能体
│   │   │   ├── car_rental.py     # 租车智能体
│   │   │   └── excursion.py      # 旅行智能体
│   │   ├── tools/                # LangChain Tool 定义
│   │   │   ├── __init__.py
│   │   │   ├── flights.py
│   │   │   ├── hotels.py
│   │   │   ├── car_rentals.py
│   │   │   ├── excursions.py
│   │   │   ├── policy.py         # RAG 政策查询
│   │   │   └── handler.py        # ToolNode + fallback
│   │   ├── models.py             # 路由/委托 Pydantic 模型
│   │   └── llm/                  # LLM Provider 抽象
│   │       ├── __init__.py
│   │       ├── base.py           # AbstractLLMProvider
│   │       ├── openai.py         # OpenAI Provider
│   │       └── deepseek.py       # DeepSeek Provider
│   ├── db/                       # 数据访问层
│   │   ├── __init__.py
│   │   ├── engine.py             # SQLAlchemy async engine + Session
│   │   ├── base.py               # DBModelBase
│   │   ├── models/               # ORM 模型
│   │   │   ├── __init__.py
│   │   │   ├── user.py           # UserModel
│   │   │   └── session.py        # ConversationSession (检查点持久化)
│   │   └── repositories/         # Repository 层
│   │       ├── __init__.py
│   │       ├── base.py           # BaseRepository
│   │       ├── user.py
│   │       └── session.py
│   └── utils/                    # 工具函数
│       ├── __init__.py
│       └── city_mapper.py        # 中英文城市映射（可扩展为数据库表）
├── migrations/                   # Alembic 数据库迁移
│   ├── alembic.ini
│   └── versions/
├── tests/                        # 测试
│   ├── __init__.py
│   ├── conftest.py               # Fixtures (async DB, test client)
│   ├── unit/
│   │   ├── test_graph_state.py
│   │   ├── test_graph_routing.py
│   │   ├── test_tools.py
│   │   └── test_security.py
│   └── integration/
│       ├── test_api_auth.py
│       ├── test_api_graph.py
│       └── test_graph_flow.py
├── data/                         # 静态数据
│   ├── travel_new.sqlite         # 初始 SQLite 数据（迁移至 MySQL 后废弃）
│   └── order_faq.md              # RAG 文档
├── scripts/                      # 运维脚本
│   ├── init_db.py                # 数据库初始化/数据迁移
│   └── seed_data.py              # 种子数据生成
├── docker/                       # Docker 配置
│   ├── Dockerfile
│   ├── docker-compose.yml
│   └── nginx.conf
├── .env.example                  # 环境变量模板
├── .env                          # 本地环境变量（不提交）
├── .gitignore
├── pyproject.toml                # Poetry 配置
├── Makefile                      # 常用命令快捷方式
└── README.md                     # 项目文档
```

---

## 3. 详细升级计划

### 3.1 项目结构重组

**目标**: 从扁平混乱结构迁移到清晰分层架构。

#### 变更清单

| 当前文件 | 目标位置 | 变更说明 |
|----------|----------|----------|
| `main.py` | `app/main.py` | 迁移至应用工厂模式 |
| `config/` | `app/core/config.py` | Dynaconf → pydantic-settings |
| `utils/jwt_utils.py` + `password_hash.py` | `app/core/security.py` | 合并安全模块 |
| `utils/handler_error.py` | `app/core/exceptions.py` | 结构化异常体系 |
| `config/log_config.py` | `app/core/logging.py` | 增强日志配置 |
| `utils/middlewares.py` | `app/middleware/auth.py` | 拆分认证中间件 |
| `utils/cors.py` | `app/middleware/cors.py` | 迁移 |
| `utils/docs_oauth2.py` | `app/middleware/auth.py` (合并) | 合并到统一认证 |
| `utils/dependencies.py` | `app/api/deps.py` | 迁移 |
| `api/` | `app/api/v1/` | 版本化 API |
| `api/schemas.py` | `app/schemas/` | 拆分 Schema |
| `api/system_mgt/` | `app/api/v1/auth.py` + `users.py` | 按资源拆分路由 |
| `api/graph_api/` | `app/api/v1/graph.py` | 迁移 |
| `graph_chat/state.py` | `app/graph/state.py` | 迁移 |
| `graph_chat/assistant.py` | `app/graph/agents/primary.py` | 拆分智能体 |
| `graph_chat/agent_assistant.py` | `app/graph/agents/{flight,hotel,car,excursion}.py` | 拆分智能体 |
| `graph_chat/graph_gradio.py` | `app/graph/graph.py` | 移除 Gradio，仅保留图定义 |
| `graph_chat/build_child_graph.py` | `app/graph/graph.py` (参数化工厂) | 消除重复，合并为工厂函数 |
| `graph_chat/base_data_model.py` | `app/graph/models.py` | 迁移 |
| `graph_chat/entry_node.py` | `app/graph/graph.py` (内联) | 合并 |
| `graph_chat/llm_tavily.py` | `app/graph/llm/` | 拆分为 Provider 抽象 |
| `graph_chat/log_utils.py` | `app/core/logging.py` | 统一日志 |
| `tools/` | `app/graph/tools/` | 内聚到图模块 + 迁移到 MySQL |
| `db/` | `app/db/` | Repository 模式 |
| `tools/init_db.py` | `scripts/init_db.py` | 脚本化 |

#### 删除文件

| 文件 | 原因 |
|------|------|
| `graph_chat/graph_gradio.py` | Gradio 移除，图定义移至 `app/graph/graph.py` |
| `graph_chat/finally_graph.py` | 与 graph_gradio.py 重复 |
| `graph_chat/第一个流程图.py` | 死代码，不可执行 |
| `graph_chat/第二个流程图.py` | 死代码，不可执行 |
| `graph_chat/第三个流程图.py` | 死代码，不可执行 |
| `graph_chat/draw_png.py` | 非生产功能 |
| `graph_chat/log_utils.py` | 统一到 `app/core/logging.py` |
| `api/__init__.py` | 当前含测试垃圾代码 |
| `torch_test/` | 测试目录，非项目代码 |

---

### 3.2 配置管理升级

**当前问题**: Dynaconf 环境切换器失效，`production.yml` 为空，密钥硬编码。

**升级方案**: pydantic-settings + `.env` 文件

```python
# app/core/config.py
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field, MySQLDsn, SecretStr
from typing import List

class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
    )

    # 应用
    APP_NAME: str = "ctrip_assistant"
    DEBUG: bool = False
    HOST: str = "0.0.0.0"
    PORT: int = 8000

    # 数据库
    DATABASE_URL: str = Field(..., description="MySQL DSN")

    # Redis
    REDIS_URL: str = "redis://localhost:6379/0"

    # JWT
    JWT_SECRET_KEY: SecretStr
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # CORS
    CORS_ORIGINS: List[str] = ["http://localhost:8080"]

    # LLM
    LLM_PROVIDER: str = "openai"  # openai | deepseek
    LLM_MODEL: str = "gpt-4o"
    LLM_API_KEY: SecretStr
    LLM_API_BASE: str = "https://api.openai.com/v1"
    LLM_TEMPERATURE: float = 0.8
    LLM_MAX_RETRIES: int = 3
    LLM_TIMEOUT: int = 60

    # Embedding
    EMBEDDING_API_KEY: SecretStr
    EMBEDDING_API_BASE: str = "https://api.openai.com/v1"
    EMBEDDING_MODEL: str = "text-embedding-3-small"

    # TAVILY (搜索工具)
    TAVILY_API_KEY: SecretStr

    # 速率限制
    RATE_LIMIT_LOGIN: str = "5/minute"
    RATE_LIMIT_GLOBAL: str = "100/minute"

    # 白名单
    AUTH_WHITELIST: List[str] = [
        "/api/v1/auth/login",
        "/api/v1/auth/register",
        "/api/v1/health",
        "/docs",
        "/openapi.json",
    ]

    # 日志
    LOG_LEVEL: str = "INFO"
    LOG_FORMAT: str = "json"  # json | console
```

```bash
# .env.example
DATABASE_URL=mysql+aiomysql://user:password@localhost:3306/ctrip_assistant
REDIS_URL=redis://localhost:6379/0
JWT_SECRET_KEY=<generate-random-64-char-hex>
LLM_PROVIDER=openai
LLM_MODEL=gpt-4o
LLM_API_KEY=sk-...
LLM_API_BASE=https://api.openai.com/v1
EMBEDDING_API_KEY=sk-...
TAVILY_API_KEY=tvly-...
```

**安全保障**:
- 所有密钥通过 `SecretStr` 类型确保不会被意外日志打印
- `.env` 文件加入 `.gitignore`
- `.env.example` 提供模板（不含真实密钥）

---

### 3.3 数据层升级

**当前问题**: SQLite (business) + MySQL (auth)，SQLite 无连接池，`echo=True` 泄露 SQL。

**升级方案**: 统一到 MySQL + Redis，Repository 模式

#### 3.3.1 MySQL 表设计

```sql
-- 用户表 (替代原 MySQL users 表)
CREATE TABLE t_user (
    id INT AUTO_INCREMENT PRIMARY KEY,
    username VARCHAR(20) NOT NULL UNIQUE,
    password_hash VARCHAR(200) NOT NULL,
    phone VARCHAR(20),
    email VARCHAR(50),
    real_name VARCHAR(50),
    icon VARCHAR(100) DEFAULT '/static/user_icon/default.jpg',
    is_active BOOLEAN DEFAULT TRUE,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_username (username),
    INDEX idx_email (email)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- 航班表 (从 SQLite flights 迁移)
CREATE TABLE flights (
    flight_id INT AUTO_INCREMENT PRIMARY KEY,
    flight_no VARCHAR(10) NOT NULL,
    departure_airport VARCHAR(10) NOT NULL,
    arrival_airport VARCHAR(10) NOT NULL,
    scheduled_departure DATETIME NOT NULL,
    scheduled_arrival DATETIME NOT NULL,
    actual_departure DATETIME,
    actual_arrival DATETIME,
    status VARCHAR(20) DEFAULT 'Scheduled',
    INDEX idx_departure (departure_airport, scheduled_departure),
    INDEX idx_arrival (arrival_airport, scheduled_arrival)
);

-- 机票表
CREATE TABLE tickets (
    ticket_no VARCHAR(13) PRIMARY KEY,
    book_ref VARCHAR(10) NOT NULL,
    passenger_id VARCHAR(20) NOT NULL,
    passenger_name VARCHAR(100),
    INDEX idx_passenger (passenger_id)
);

-- 机票-航班关联
CREATE TABLE ticket_flights (
    ticket_no VARCHAR(13) NOT NULL,
    flight_id INT NOT NULL,
    fare_conditions VARCHAR(20),
    amount DECIMAL(10,2),
    PRIMARY KEY (ticket_no, flight_id),
    FOREIGN KEY (ticket_no) REFERENCES tickets(ticket_no) ON DELETE CASCADE,
    FOREIGN KEY (flight_id) REFERENCES flights(flight_id)
);

-- 酒店表
CREATE TABLE hotels (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    location VARCHAR(100),
    price_tier VARCHAR(20),
    checkin_date DATE,
    checkout_date DATE,
    booked BOOLEAN DEFAULT FALSE,
    INDEX idx_location (location),
    INDEX idx_booked (booked)
);

-- 租车表
CREATE TABLE car_rentals (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    location VARCHAR(100),
    price_tier VARCHAR(20),
    start_date DATE,
    end_date DATE,
    booked BOOLEAN DEFAULT FALSE,
    INDEX idx_location (location)
);

-- 旅行推荐表
CREATE TABLE trip_recommendations (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    location VARCHAR(100),
    keywords TEXT,
    details TEXT,
    booked BOOLEAN DEFAULT FALSE,
    INDEX idx_location (location)
);

-- 登机牌
CREATE TABLE boarding_passes (
    ticket_no VARCHAR(13) NOT NULL,
    flight_id INT NOT NULL,
    boarding_no INT NOT NULL,
    seat_no VARCHAR(5),
    PRIMARY KEY (ticket_no, flight_id),
    FOREIGN KEY (ticket_no) REFERENCES tickets(ticket_no) ON DELETE CASCADE,
    FOREIGN KEY (flight_id) REFERENCES flights(flight_id)
);

-- 对话会话 (LangGraph 检查点持久化)
CREATE TABLE conversation_sessions (
    id VARCHAR(36) PRIMARY KEY,
    passenger_id VARCHAR(20),
    thread_id VARCHAR(36) NOT NULL,
    checkpoint_data JSON NOT NULL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_thread (thread_id),
    INDEX idx_passenger (passenger_id)
);
```

#### 3.3.2 SQLAlchemy 配置

```python
# app/db/engine.py
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from app.core.config import settings

engine = create_async_engine(
    str(settings.DATABASE_URL),
    echo=settings.DEBUG,  # 仅 DEBUG 模式打印 SQL
    pool_size=20,
    max_overflow=10,
    pool_pre_ping=True,   # 连接健康检查
    pool_recycle=3600,    # 连接回收
)

AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)
```

#### 3.3.3 Repository 层

```python
# app/db/repositories/base.py
from typing import Generic, TypeVar, Type, Optional, List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete

ModelType = TypeVar("ModelType")

class BaseRepository(Generic[ModelType]):
    def __init__(self, model: Type[ModelType]):
        self.model = model

    async def get_by_id(self, session: AsyncSession, pk: int) -> Optional[ModelType]:
        return await session.get(self.model, pk)

    async def get_all(self, session: AsyncSession, *, skip: int = 0, limit: int = 100) -> List[ModelType]:
        stmt = select(self.model).offset(skip).limit(limit)
        result = await session.execute(stmt)
        return result.scalars().all()

    async def create(self, session: AsyncSession, **kwargs) -> ModelType:
        obj = self.model(**kwargs)
        session.add(obj)
        await session.commit()
        await session.refresh(obj)
        return obj

    async def update(self, session: AsyncSession, pk: int, **kwargs) -> Optional[ModelType]:
        obj = await self.get_by_id(session, pk)
        if obj:
            for key, val in kwargs.items():
                setattr(obj, key, val)
            await session.commit()
            await session.refresh(obj)
        return obj

    async def delete(self, session: AsyncSession, pk: int) -> bool:
        obj = await self.get_by_id(session, pk)
        if obj:
            await session.delete(obj)
            await session.commit()
            return True
        return False
```

#### 3.3.4 工具函数迁移

所有工具函数从 `sqlite3.connect(db)` 迁移为通过 Repository 访问 MySQL:

```python
# app/graph/tools/flights.py (示例)
from langchain_core.tools import tool
from app.db.repositories import FlightRepository

@tool
async def search_flights(
    departure_airport: Optional[str] = None,
    arrival_airport: Optional[str] = None,
    start_time: Optional[datetime] = None,
    end_time: Optional[datetime] = None,
    limit: int = 20,
) -> List[Dict]:
    """使用 Repository 查询航班（异步）"""
    repo = FlightRepository()
    async with AsyncSessionLocal() as session:
        results = await repo.search(
            session,
            departure=departure_airport,
            arrival=arrival_airport,
            start=start_time,
            end=end_time,
            limit=limit,
        )
        return [r.to_dict() for r in results]
```

#### 3.3.5 数据迁移脚本

```python
# scripts/migrate_sqlite_to_mysql.py
"""
一次性脚本：将 travel_new.sqlite 中的数据迁移到 MySQL。
"""
import asyncio
import sqlite3
import pandas as pd
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from app.core.config import settings

async def migrate():
    # 1. 从 SQLite 读取
    sqlite_conn = sqlite3.connect("data/travel_new.sqlite")
    tables = ["flights", "tickets", "ticket_flights", "hotels",
              "car_rentals", "trip_recommendations", "boarding_passes"]

    engine = create_async_engine(str(settings.DATABASE_URL))

    for table in tables:
        df = pd.read_sql(f"SELECT * FROM {table}", sqlite_conn)
        # 2. 写入 MySQL
        async with engine.begin() as conn:
            df.to_sql(table, conn, if_exists="replace", index=False)
        print(f"Migrated {table}: {len(df)} rows")

    sqlite_conn.close()
    await engine.dispose()

if __name__ == "__main__":
    asyncio.run(migrate())
```

---

### 3.4 API 与安全层升级

#### 3.4.1 安全升级

| 改进项 | 实现 |
|--------|------|
| **JWT 密钥** | 从环境变量 `JWT_SECRET_KEY` 读取，随机 64 字符 hex |
| **密码哈希** | 保持 bcrypt，增加 Argon2 选项 |
| **令牌撤销** | Redis 黑名单，`POST /auth/logout` 加入黑名单 |
| **Refresh Token** | 短期 access token (30min) + 长期 refresh token (7d) |
| **速率限制** | `slowapi` + Redis 后端，登录接口 `5/min` |
| **输入验证** | `EmailStr`、密码 `min_length=8`、批量删除 `max_length=100` |
| **SQL echo** | 仅 `DEBUG=True` 时启用 |
| **白名单** | `re.fullmatch` 替代 `re.match`，防止前缀绕过 |
| **CORS** | 生产 origin 通过配置动态注入 |

#### 3.4.2 JWT 增强

```python
# app/core/security.py
def create_access_token(subject: str) -> str:
    expires = datetime.utcnow() + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    return jwt.encode(
        {"sub": subject, "exp": expires, "type": "access"},
        settings.JWT_SECRET_KEY.get_secret_value(),
        algorithm=settings.JWT_ALGORITHM,
    )

def create_refresh_token(subject: str) -> str:
    expires = datetime.utcnow() + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
    return jwt.encode(
        {"sub": subject, "exp": expires, "type": "refresh"},
        settings.JWT_SECRET_KEY.get_secret_value(),
        algorithm=settings.JWT_ALGORITHM,
    )
```

#### 3.4.3 异常体系

```python
# app/core/exceptions.py
from fastapi import HTTPException, status

class AppException(HTTPException):
    """应用异常基类"""
    def __init__(self, detail: str, status_code: int = 500):
        super().__init__(status_code=status_code, detail=detail)

class AuthenticationError(AppException):
    def __init__(self, detail: str = "认证失败"):
        super().__init__(detail=detail, status_code=status.HTTP_401_UNAUTHORIZED)

class NotFoundError(AppException):
    def __init__(self, detail: str = "资源不存在"):
        super().__init__(detail=detail, status_code=status.HTTP_404_NOT_FOUND)

class ValidationError(AppException):
    def __init__(self, detail: str = "数据验证失败"):
        super().__init__(detail=detail, status_code=status.HTTP_422_UNPROCESSABLE_ENTITY)

class RateLimitError(AppException):
    def __init__(self, detail: str = "请求过于频繁"):
        super().__init__(detail=detail, status_code=status.HTTP_429_TOO_MANY_REQUESTS)

class LLMServiceError(AppException):
    def __init__(self, detail: str = "AI 服务暂时不可用"):
        super().__init__(detail=detail, status_code=status.HTTP_503_SERVICE_UNAVAILABLE)
```

#### 3.4.4 API 端点设计

| 当前 | 新端点 | 方法 | 说明 |
|------|--------|------|------|
| `POST /api/login/` | `POST /api/v1/auth/login` | POST | JSON body 登录 |
| `POST /api/auth/` | `POST /api/v1/auth/token` | POST | OAuth2 表单（给 Swagger） |
| `POST /api/register/` | `POST /api/v1/auth/register` | POST | 用户注册 |
| — | `POST /api/v1/auth/refresh` | POST | 刷新令牌 |
| — | `POST /api/v1/auth/logout` | POST | 登出（令牌加入黑名单） |
| `GET /api/users/getUsers/` | `GET /api/v1/users` | GET | 分页用户列表 |
| `GET /api/users/{pk}/` | `GET /api/v1/users/{user_id}` | GET | 获取单个用户 |
| `PATCH /api/users/{pk}/` | `PATCH /api/v1/users/{user_id}` | PATCH | 更新用户 |
| `POST /api/users/delete/` | `DELETE /api/v1/users` | DELETE | 批量删除（body: `{ids: [...]}`） |
| `POST /api/graph/` | `POST /api/v1/graph/chat` | POST | 多智能体对话 |
| — | `GET /api/v1/health` | GET | 健康检查 |

#### 3.4.5 中间件栈

```python
# app/main.py
def create_app() -> FastAPI:
    app = FastAPI(title="携程 AI 助手", version="1.0.0")

    # 中间件顺序很重要！
    app.add_middleware(RequestIDMiddleware)        # 1. 注入 X-Request-ID
    app.add_middleware(CORSMiddleware, ...)         # 2. CORS
    app.add_middleware(RateLimitMiddleware)         # 3. 速率限制
    app.add_middleware(AuthenticationMiddleware)    # 4. JWT 认证
    app.add_middleware(RequestLoggingMiddleware)    # 5. 请求日志

    # 异常处理
    app.add_exception_handler(HTTPException, http_exception_handler)
    app.add_exception_handler(RequestValidationError, validation_exception_handler)
    app.add_exception_handler(Exception, unhandled_exception_handler)

    # 路由
    app.include_router(v1_router, prefix="/api/v1")

    # 生命周期
    @app.on_event("startup")
    async def startup():
        await init_db()
        await init_redis()

    @app.on_event("shutdown")
    async def shutdown():
        await close_db()
        await close_redis()

    return app
```

---

### 3.5 LLM 与 Agent 系统升级

#### 3.5.1 LLM Provider 抽象层

```python
# app/graph/llm/base.py
from abc import ABC, abstractmethod
from langchain_core.language_models import BaseChatModel

class AbstractLLMProvider(ABC):
    @abstractmethod
    def get_chat_model(self) -> BaseChatModel:
        ...

    @abstractmethod
    def get_embedding_model(self):
        ...

# app/graph/llm/openai.py
class OpenAIProvider(AbstractLLMProvider):
    def get_chat_model(self) -> BaseChatModel:
        return ChatOpenAI(
            model=settings.LLM_MODEL,
            api_key=settings.LLM_API_KEY.get_secret_value(),
            base_url=settings.LLM_API_BASE,
            temperature=settings.LLM_TEMPERATURE,
            max_retries=settings.LLM_MAX_RETRIES,
            timeout=settings.LLM_TIMEOUT,
        )
```

#### 3.5.2 智能体重试与超时

```python
# app/graph/graph.py
class CtripAssistant:
    MAX_RETRIES = 3

    def __call__(self, state: State, config: RunnableConfig):
        for attempt in range(self.MAX_RETRIES):
            try:
                result = self.runnable.invoke(state)
                if result.tool_calls or (result.content and not self._is_empty(result.content)):
                    return {"messages": result}
            except Exception as e:
                if attempt == self.MAX_RETRIES - 1:
                    raise LLMServiceError(f"LLM 调用失败: {e}")
                time.sleep(2 ** attempt)  # 指数退避

            # 空内容重试
            messages = state["messages"] + [("user", "请提供一个真实的输出。")]
            state = {**state, "messages": messages}

        raise LLMServiceError("达到最大重试次数")
```

#### 3.5.3 参数化子图工厂（消除 76% 重复代码）

```python
# app/graph/graph.py
def build_sub_graph(
    builder: StateGraph,
    entry_node_name: str,
    assistant_node_name: str,
    safe_tools_node_name: str,
    sensitive_tools_node_name: str,
    assistant_name: str,
    dialog_state: str,
    runnable: Runnable,
    safe_tools: List,
    sensitive_tools: List,
) -> StateGraph:
    """参数化子图构建器 — 一个函数替代 4 个重复构建器"""

    # 入口节点
    builder.add_node(
        entry_node_name,
        create_entry_node(assistant_name, dialog_state),
    )
    # 子智能体
    builder.add_node(assistant_node_name, CtripAssistant(runnable))
    builder.add_edge(entry_node_name, assistant_node_name)

    # 工具节点
    builder.add_node(safe_tools_node_name, create_tool_node_with_fallback(safe_tools))
    builder.add_node(sensitive_tools_node_name, create_tool_node_with_fallback(sensitive_tools))

    # 路由
    def route(state: dict) -> str:
        route = tools_condition(state)
        if route == END:
            return END
        tool_calls = state["messages"][-1].tool_calls
        if any(tc["name"] == CompleteOrEscalate.__name__ for tc in tool_calls):
            return "leave_skill"
        safe_names = [t.name for t in safe_tools]
        if all(tc["name"] in safe_names for tc in tool_calls):
            return safe_tools_node_name
        return sensitive_tools_node_name

    builder.add_conditional_edges(
        assistant_node_name,
        route,
        [safe_tools_node_name, sensitive_tools_node_name, "leave_skill", END],
    )
    builder.add_edge(safe_tools_node_name, assistant_node_name)
    builder.add_edge(sensitive_tools_node_name, assistant_node_name)
    return builder
```

#### 3.5.4 检查点持久化

```python
# 替换 MemorySaver → MySQL 持久化
from langgraph.checkpoint.mysql import MySQLSaver

# 或使用自定义实现
checkpointer = MySQLCheckpointer(AsyncSessionLocal)
graph = builder.compile(
    checkpointer=checkpointer,
    interrupt_before=[...],
)
```

#### 3.5.5 智能体提示词修正

```
# 修复前: <Fllights> (拼写错误)
# 修复后: <Flights>

# 修复前: time=datetime.now() 在模块导入时固化
# 修复后: 使用 RunnableLambda 动态注入时间

# 修复前: 中英文混合提示词
# 修复后: 统一为中文系统提示 + 英文工具名称（或全中文）
```

---

### 3.6 可观测性升级

**目标**: 基础日志 + 健康检查（用户选择）

#### 3.6.1 结构化日志（JSON 格式）

```python
# app/core/logging.py
import logging
import json
from datetime import datetime

class JsonFormatter(logging.Formatter):
    def format(self, record):
        log_entry = {
            "timestamp": datetime.utcnow().isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
            "message": record.getMessage(),
        }
        if hasattr(record, "request_id"):
            log_entry["request_id"] = record.request_id
        if record.exc_info:
            log_entry["exception"] = self.formatException(record.exc_info)
        return json.dumps(log_entry, ensure_ascii=False)

def setup_logging():
    handler = logging.StreamHandler()
    handler.setFormatter(JsonFormatter())

    root = logging.getLogger()
    root.setLevel(settings.LOG_LEVEL)
    root.addHandler(handler)

    # 文件日志（生产环境）
    if not settings.DEBUG:
        file_handler = logging.handlers.RotatingFileHandler(
            "logs/app.log", maxBytes=10*1024*1024, backupCount=5
        )
        file_handler.setFormatter(JsonFormatter())
        root.addHandler(file_handler)
```

#### 3.6.2 健康检查端点

```python
# app/api/v1/health.py
router = APIRouter()

@router.get("/health")
async def health_check():
    db_ok = await check_database()
    redis_ok = await check_redis()
    llm_ok = await check_llm()

    status_code = 200 if all([db_ok, redis_ok]) else 503
    return JSONResponse(
        content={
            "status": "healthy" if status_code == 200 else "degraded",
            "checks": {
                "database": "ok" if db_ok else "error",
                "redis": "ok" if redis_ok else "error",
                "llm": "ok" if llm_ok else "error",
            },
            "version": "1.0.0",
            "timestamp": datetime.utcnow().isoformat(),
        },
        status_code=status_code,
    )
```

---

### 3.7 测试体系

**当前状态**: 零测试覆盖。

**目标**: 三层测试金字塔

```
        ┌─────────┐
        │  E2E    │  少量关键流程（登录 + Graph 对话）
        │  10%    │
       ┌┴─────────┴┐
       │ Integration│  中型: API 端点测试 + DB 交互
       │    30%     │
      ┌┴────────────┴┐
      │   Unit        │  主力: 路由逻辑、工具函数、安全模块
      │    60%        │
      └───────────────┘
```

#### 3.7.1 测试基础设施

```python
# tests/conftest.py
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from app.main import create_app

@pytest_asyncio.fixture
async def async_client():
    app = create_app()
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        yield client

@pytest_asyncio.fixture
async def async_db_session():
    # 使用测试数据库
    async with AsyncSessionLocal() as session:
        yield session
        await session.rollback()  # 测试后回滚
```

#### 3.7.2 关键测试用例

| 分类 | 测试内容 |
|------|----------|
| **Unit: 图路由** | `route_primary_assistant` 在所有分支正确返回节点名 |
| **Unit: 图状态** | `update_dialog_stack` 的 push/pop/noop 行为 |
| **Unit: 安全** | JWT 创建/解码、密码哈希/验证 |
| **Unit: 工具** | `search_flights` 参数化查询正确性 |
| **Integration: API** | 注册→登录→获取令牌→访问受保护端点 |
| **Integration: API** | 无效令牌返回 401 |
| **Integration: API** | 登录速率限制生效 |
| **E2E: Graph** | 完整对话流程：查航班→改签→确认 |

---

### 3.8 部署与运维

#### 3.8.1 Dockerfile

```dockerfile
# docker/Dockerfile
FROM python:3.11-slim

WORKDIR /app

# 依赖安装
COPY pyproject.toml poetry.lock ./
RUN pip install poetry && poetry config virtualenvs.create false && poetry install --no-dev

# 应用代码
COPY app/ ./app/
COPY data/order_faq.md ./data/

EXPOSE 8000

CMD ["uvicorn", "app.main:create_app", "--host", "0.0.0.0", "--port", "8000", "--factory"]
```

#### 3.8.2 Docker Compose

```yaml
# docker/docker-compose.yml
version: '3.8'

services:
  app:
    build:
      context: ..
      dockerfile: docker/Dockerfile
    ports:
      - "8000:8000"
    env_file: ../.env
    depends_on:
      mysql:
        condition: service_healthy
      redis:
        condition: service_healthy
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/api/v1/health"]
      interval: 30s
      timeout: 10s
      retries: 3

  mysql:
    image: mysql:8.0
    environment:
      MYSQL_ROOT_PASSWORD: ${MYSQL_ROOT_PASSWORD}
      MYSQL_DATABASE: ctrip_assistant
    ports:
      - "3306:3306"
    volumes:
      - mysql_data:/var/lib/mysql
    healthcheck:
      test: ["CMD", "mysqladmin", "ping", "-h", "localhost"]
      interval: 10s
      retries: 5

  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 10s
      retries: 5

  nginx:
    image: nginx:alpine
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./nginx.conf:/etc/nginx/nginx.conf:ro
    depends_on:
      - app

volumes:
  mysql_data:
```

#### 3.8.3 Makefile

```makefile
.PHONY: dev test build up down migrate

dev:
	uvicorn app.main:create_app --reload --factory

test:
	pytest tests/ -v --cov=app --cov-report=term

build:
	docker compose -f docker/docker-compose.yml build

up:
	docker compose -f docker/docker-compose.yml up -d

down:
	docker compose -f docker/docker-compose.yml down

migrate:
	alembic upgrade head

migrate-data:
	python scripts/migrate_sqlite_to_mysql.py
```

---

## 4. 迁移路线图

### Phase 0: 紧急修复 (预计 1-2 天)

> **目标**: 消除当前阻断级安全风险，不改变架构

| 步骤 | 内容 | 优先级 |
|------|------|--------|
| P0.1 | 修复 `tools/__init__.py:9,12` f-string bug | 🔴 |
| P0.2 | 修复 `InDBMixin` 导入断裂 | 🔴 |
| P0.3 | 将所有 API 密钥/Tavily Key 移至 `.env`，从源码移除 | 🔴 |
| P0.4 | 生成新的 JWT 密钥替代公开示例密钥 | 🔴 |
| P0.5 | 修改 MySQL 数据库密码 | 🔴 |
| P0.6 | 删除 `api/__init__.py` 中的垃圾测试代码 | 🟡 |
| P0.7 | 将 `db/__init__.py` 的 `echo=True` 改为条件判断 | 🟡 |

### Phase 1: 项目结构重组 + 配置升级 (预计 3-4 天)

| 步骤 | 内容 |
|------|------|
| P1.1 | 初始化 Poetry (`pyproject.toml`) |
| P1.2 | 创建新目录结构 (app/core, app/api, app/db, app/graph 等) |
| P1.3 | 实现 `app/core/config.py` (pydantic-settings) |
| P1.4 | 实现 `app/core/security.py` (JWT + 密码) |
| P1.5 | 实现 `app/core/exceptions.py` (异常体系) |
| P1.6 | 实现 `app/core/logging.py` (结构化日志) |
| P1.7 | 实现 `app/middleware/` (认证/限流/请求ID) |
| P1.8 | 删除死代码文件 (3 个流程图, finally_graph, draw_png, torch_test) |

### Phase 2: 数据层升级 (预计 3-4 天)

| 步骤 | 内容 |
|------|------|
| P2.1 | 在 MySQL 中创建所有新表 (flights, hotels, car_rentals 等) |
| P2.2 | 编写数据迁移脚本 `migrate_sqlite_to_mysql.py` |
| P2.3 | 实现 SQLAlchemy async engine + Repository 层 |
| P2.4 | 将所有工具函数从 `sqlite3.connect` 迁移到 MySQL Repository |
| P2.5 | 实现对话会话持久化 (LangGraph checkpointer → MySQL) |
| P2.6 | 编写 Alembic 迁移配置 |

### Phase 3: LLM + Agent 系统升级 (预计 3-5 天)

| 步骤 | 内容 |
|------|------|
| P3.1 | 实现 LLM Provider 抽象层 (OpenAI / DeepSeek) |
| P3.2 | 移除本地 Qwen-7B 配置，切换到云端 LLM |
| P3.3 | 实现参数化子图工厂（消除 `build_child_graph.py` 重复代码）|
| P3.4 | 修复 `while True` 为有限重试 + 指数退避 |
| P3.5 | 修复提示词拼写错误和时间固化问题 |
| P3.6 | 移除 Gradio UI，提取纯图定义 |
| P3.7 | 实现 `graph_service.py` 编排服务 |

### Phase 4: API + 测试 (预计 4-5 天)

| 步骤 | 内容 |
|------|------|
| P4.1 | 重写所有 API 端点 (v1, async) |
| P4.2 | 实现 Refresh Token + 令牌黑名单 |
| P4.3 | 实现速率限制中间件 |
| P4.4 | 实现健康检查端点 |
| P4.5 | 编写单元测试 (图路由、状态、安全、工具) |
| P4.6 | 编写集成测试 (API 端点、图谱流程) |
| P4.7 | 实现 API 层面的输入验证增强 |

### Phase 5: 部署 (预计 2-3 天)

| 步骤 | 内容 |
|------|------|
| P5.1 | 编写 Dockerfile |
| P5.2 | 编写 docker-compose.yml (app + mysql + redis + nginx) |
| P5.3 | 编写 nginx.conf (反向代理) |
| P5.4 | 编写 .env.example 和 README.md |
| P5.5 | 端到端部署验证 |

**预计总工期**: 15-21 天

---

## 5. 待确认问题

| # | 问题 | 建议 |
|---|------|------|
| Q1 | `order_faq.md` 中的瑞士航空 FAQ 数据 — 这是生产环境的 RAG 数据源吗？需要支持更新机制吗？ | 确认 RAG 文档管理策略 |
| Q2 | 中文城市映射 (`location_trans.py`) 目前仅 8 个城市 — 是否需要扩展为数据库表？ | 建议改为 DB 表，支持动态维护 |
| Q3 | Tavily 搜索工具在生产环境还需要吗？如需保留，需要企业版 API Key | 确认搜索工具是否必需 |
| Q4 | `passenger_id` 来自认证用户的身份绑定 — 当前用户系统 (UserModel) 与乘客 ID 如何关联？ | 需要明确 User ↔ Passenger 关系 |
| Q5 | 是否需要 API 文档国际化（当前是中文）？ | 确认文档语言偏好 |
| Q6 | 日志第三方采集方案（如 ELK / Loki）需要预留接入吗？ | 当前方案是 JSON 格式文件日志，可被任意采集器读取 |

---

## 附录 A: 当前文件-目标文件映射表

| 当前 | 目标 |
|------|------|
| `main.py` | `app/main.py` |
| `config/__init__.py` | `app/core/config.py` |
| `config/development.yml` | 废弃 → `.env` |
| `config/production.yml` | 废弃 → `.env` |
| `config/log_config.py` | `app/core/logging.py` |
| `utils/jwt_utils.py` | `app/core/security.py` |
| `utils/password_hash.py` | `app/core/security.py` |
| `utils/handler_error.py` | `app/core/exceptions.py` |
| `utils/middlewares.py` | `app/middleware/auth.py` |
| `utils/cors.py` | `app/middleware/cors.py` |
| `utils/docs_oauth2.py` | `app/middleware/auth.py` |
| `utils/dependencies.py` | `app/api/deps.py` |
| `api/routers.py` | `app/api/v1/router.py` |
| `api/graph_api/graph_views.py` | `app/api/v1/graph.py` |
| `api/graph_api/graph_schemas.py` | `app/schemas/graph.py` |
| `api/system_mgt/user_views.py` | `app/api/v1/auth.py` + `users.py` |
| `api/system_mgt/user_schemas.py` | `app/schemas/user.py` |
| `api/schemas.py` | `app/schemas/common.py` |
| `db/__init__.py` | `app/db/engine.py` + `base.py` |
| `db/dao.py` | `app/db/repositories/base.py` |
| `db/system_mgt/models.py` | `app/db/models/user.py` |
| `db/system_mgt/user_dao.py` | `app/db/repositories/user.py` |
| `graph_chat/state.py` | `app/graph/state.py` |
| `graph_chat/graph_gradio.py` | `app/graph/graph.py` (移除 Gradio) |
| `graph_chat/assistant.py` | `app/graph/agents/primary.py` |
| `graph_chat/agent_assistant.py` | `app/graph/agents/{flight,hotel,car,excursion}.py` |
| `graph_chat/build_child_graph.py` | `app/graph/graph.py` (参数化工厂函数) |
| `graph_chat/entry_node.py` | `app/graph/graph.py` (内联) |
| `graph_chat/base_data_model.py` | `app/graph/models.py` |
| `graph_chat/llm_tavily.py` | `app/graph/llm/openai.py` |
| `graph_chat/log_utils.py` | `app/core/logging.py` |
| `tools/__init__.py` | `app/core/config.py` (db 路径移至配置) |
| `tools/flights_tools.py` | `app/graph/tools/flights.py` |
| `tools/hotels_tools.py` | `app/graph/tools/hotels.py` |
| `tools/car_tools.py` | `app/graph/tools/car_rentals.py` |
| `tools/trip_tools.py` | `app/graph/tools/excursions.py` |
| `tools/retriever_vector.py` | `app/graph/tools/policy.py` |
| `tools/tools_handler.py` | `app/graph/tools/handler.py` |
| `tools/location_trans.py` | `app/utils/city_mapper.py` |
| `tools/init_db.py` | `scripts/init_db.py` |

---

## 附录 B: 已知 Bug 修复

| Bug | 修复方案 |
|-----|----------|
| `tools/__init__.py:9,12` 缺少 `f` 前缀 | 移至 `app/core/config.py`，路径由配置管理 |
| `api/schemas.py` 中 `InDBMixin` 被注释 | 在 `app/schemas/common.py` 中重新定义 |
| `config/production.yml` 为空 | pydantic-settings 替代，环境切换由 `.env` 控制 |
| `echo=True` 在生产泄露 SQL | 改为 `echo=settings.DEBUG` |

---

> **文档状态**: 等待审核  
> **下一步**: 确认第 5 节待确认问题后，进入 Phase 0 紧急修复
