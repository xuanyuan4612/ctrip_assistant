# 携程 AI 助手 — 生产级开发文档

> **版本**: v2.1 (增强多 Agent 架构)  
> **日期**: 2026-04-28  
> **文档范围**: 完整生产级架构 —— 从应用代码到基础设施、从 Agent 治理到决策智能、从非功能需求到迁移路线图  
> **设计原则**: 架构先行 · 分层清晰 · 决策可追溯 · 故障可降级 · 知识可治理  

---

## 目录

### [第一部分: 项目概述与现状评估](#第一部分项目概述与现状评估)
- [1.1 项目定位](#11-项目定位)
- [1.2 现状评估](#12-现状评估)
- [1.3 关键问题清单](#13-关键问题清单)

### [第二部分: 目标架构](#第二部分目标架构)
- [2.1 架构决策 (ADR)](#21-架构决策-adr)
- [2.2 六层分层架构](#22-六层分层架构)
- [2.3 目标项目结构](#23-目标项目结构)

### [第三部分: 各层详细设计](#第三部分各层详细设计)
- [3.1 Layer 1: 基础层](#31-layer-1-基础层)
- [3.2 Layer 2: 能力层](#32-layer-2-能力层)
- [3.3 Layer 3: Agent 层](#33-layer-3-agent-层)
- [3.4 Layer 4: 编排层](#34-layer-4-编排层)
- [3.5 Layer 5: 表现层](#35-layer-5-表现层)
- [3.6 Layer 6: 治理层](#36-layer-6-治理层)

### [第四部分: 核心子系统设计](#第四部分核心子系统设计)
- [4.1 RAG 系统](#41-rag-系统)
- [4.2 记忆与检查点机制](#42-记忆与检查点机制)
- [4.3 跨 Agent 用户身份统一](#43-跨-agent-用户身份统一)
- [4.4 城市映射数据库化](#44-城市映射数据库化)
- [4.5 文档处理管线](#45-文档处理管线)
- [4.6 分布式检索架构](#46-分布式检索架构)

### [第五部分: Agent 决策智能](#第五部分-agent-决策智能)
- [5.1 决策溯源](#51-决策溯源)
- [5.2 置信度估计](#52-置信度估计)
- [5.3 确定性重放](#53-确定性重放)
- [5.4 知识生命周期管理](#54-知识生命周期管理)
- [5.5 Agent 协作模式](#55-agent-协作模式)
- [5.6 Agent 自检机制](#56-agent-自检机制)

### [第六部分: 非功能性架构](#第六部分非功能性架构)
- [6.1 SLO 定义](#61-slo-定义)
- [6.2 故障模式分析 (FMEA)](#62-故障模式分析-fmea)
- [6.3 容量规划模型](#63-容量规划模型)
- [6.4 多租户隔离架构](#64-多租户隔离架构)
- [6.5 数据隐私合规](#65-数据隐私合规)
- [6.6 用户体验度量](#66-用户体验度量)

### [第七部分: 风险治理与迁移路线图](#第七部分风险治理与迁移路线图)
- [7.1 技术风险登记册](#71-技术风险登记册)
- [7.2 现状 vs 目标差距矩阵](#72-现状-vs-目标差距矩阵)
- [7.3 分阶段迁移路线图](#73-分阶段迁移路线图)

### [第八部分: 部署与运维](#第八部分部署与运维)
- [8.1 Docker Compose 拓扑](#81-docker-compose-拓扑)
- [8.2 高可用拓扑](#82-高可用拓扑)
- [8.3 监控告警体系](#83-监控告警体系)
- [8.4 测试体系](#84-测试体系)

### [附录](#附录)
- [附录 A: 文件映射表](#附录-a-文件映射表)
- [附录 B: 依赖变更清单](#附录-b-依赖变更清单)
- [附录 C: 技术栈总览](#附录-c-技术栈总览)

---

# 第一部分: 项目概述与现状评估

## 1.1 项目定位

| 维度 | 说明 |
|------|------|
| **名称** | 携程 AI 助手 (Ctrip AI Assistant) |
| **形态** | 多智能体对话系统 (LangGraph Supervisor 模式) |
| **入口** | FastAPI REST API (移除 Gradio) |
| **LLM** | 云端 LLM (OpenAI / DeepSeek)，Provider 抽象层可切换 |
| **数据库** | MySQL (业务数据) + PostgreSQL (Agent 记忆) |
| **用户规模** | 数千认证用户 |
| **文档规模** | 50TB 混合文档 (PDF / Office / 结构化数据 / 实时流) |
| **部署** | Docker Compose 起步，预留 K8s 迁移路径 |

## 1.2 现状评估

### 1.2.1 项目概览

| 维度 | 当前状态 |
|------|----------|
| **入口** | FastAPI REST API + Gradio 交互测试 UI |
| **LLM** | 本地 Qwen-7B + 多个云端 LLM（注释中） |
| **数据库** | SQLite（业务数据）+ MySQL（用户认证），双数据库 |
| **Agent 框架** | LangGraph StateGraph，多智能体 Supervisor 模式 |
| **配置** | Dynaconf，仅 development.yml 有内容 |
| **测试** | 零覆盖 |
| **部署** | 裸 Python 进程 |

### 1.2.2 当前代码结构

```
ctrip_assistant/
├── main.py                     # FastAPI 入口
├── requirements.txt            # 依赖 (110 个包)
├── config/                     # Dynaconf 配置
│   ├── __init__.py
│   ├── development.yml         # 仅开发配置 (生产为空)
│   ├── production.yml          # 空文件
│   └── log_config.py
├── api/                        # FastAPI 路由
│   ├── __init__.py             # 含测试垃圾代码
│   ├── routers.py
│   ├── schemas.py              # 含断裂导入
│   ├── graph_api/
│   │   ├── graph_views.py      # 图表 API 端点
│   │   └── graph_schemas.py    # 硬编码 passenger_id
│   └── system_mgt/
│       ├── user_views.py       # 用户 CRUD + 登录
│       └── user_schemas.py     # 用户 Schema (导入断裂)
├── db/                         # 数据层
│   ├── __init__.py             # SQLAlchemy + echo=True bug
│   ├── dao.py                  # 通用 CRUD
│   └── system_mgt/
│       ├── models.py           # UserModel (无 passenger_id)
│       └── user_dao.py
├── graph_chat/                 # 多智能体图
│   ├── state.py                # State TypedDict
│   ├── graph_gradio.py         # 活跃图 + Gradio UI
│   ├── finally_graph.py        # 重复的图 (无 UI)
│   ├── assistant.py            # CtripAssistant + 主 Agent
│   ├── agent_assistant.py      # 4 个子 Agent
│   ├── build_child_graph.py    # 76% 重复模板代码
│   ├── entry_node.py           # 入口节点工厂
│   ├── base_data_model.py      # 路由 Pydantic 模型
│   ├── llm_tavily.py           # LLM 客户端 + 硬编码 API Key
│   ├── 第一个流程图.py          # 死代码
│   ├── 第二个流程图.py          # 死代码
│   └── 第三个流程图.py          # 死代码
├── tools/                      # 工具函数
│   ├── __init__.py             # f-string bug
│   ├── flights_tools.py        # 纯 sqlite3 连接
│   ├── hotels_tools.py         # 无身份验证
│   ├── car_tools.py            # 无身份验证
│   ├── trip_tools.py           # 无身份验证
│   ├── retriever_vector.py     # numpy 内存检索 + 硬编码 API Key
│   ├── location_trans.py       # 8 城市硬编码字典
│   ├── tools_handler.py
│   └── init_db.py
├── utils/                      # 工具
│   ├── jwt_utils.py            # JWT 创建
│   ├── password_hash.py        # bcrypt 密码哈希
│   ├── middlewares.py           # JWT 验证中间件
│   ├── cors.py                 # CORS 配置
│   ├── dependencies.py         # DB 会话依赖
│   ├── docs_oauth2.py          # Swagger OAuth2
│   └── handler_error.py        # 基础异常处理
├── static/                     # 静态文件
├── logs/                       # 日志目录 (空)
├── torch_test/                 # 测试代码 (非项目)
├── order_faq.md                # RAG 文档 (瑞士航空 FAQ)
├── travel_new.sqlite           # SQLite 业务数据库
└── travel2.sqlite              # SQLite 备份
```

## 1.3 关键问题清单

### 1.3.1 P0 阻断级 (7 项)

| # | 问题 | 位置 | 影响 |
|---|------|------|------|
| 1 | **JWT 密钥公开** — 使用 FastAPI 官方教程示例密钥 | `config/development.yml:15` | 任何人可伪造 JWT 令牌 |
| 2 | **数据库密码明文** — `root:123123` 存储于版本控制 | `config/development.yml:10-11` | 数据库凭据泄露 |
| 3 | **API 密钥硬编码** — Tavily、OpenAI Embedding 密钥在源码中 | `llm_tavily.py:43`, `retriever_vector.py:25` | API 密钥泄露 |
| 4 | **生产配置为空** — `production.yml` 0 字节 | `config/__init__.py`, `config/production.yml` | 生产回退到开发配置 |
| 5 | **`tools/__init__.py` f-string Bug** | `tools/__init__.py:9,12` | `update_dates()` 静默失败 |
| 6 | **`InDBMixin` 导入断裂** | `api/schemas.py:14-22`, `user_schemas.py:6` | 运行时 ImportError |
| 7 | **SQLite 无连接池** — 每次工具调用新建连接 | 所有 `tools/*_tools.py` | 并发下连接泄漏 |

### 1.3.2 P1 高风险 (8 项)

| # | 问题 | 位置 |
|---|------|------|
| 8 | `sqlalchemy echo=True` 在生产记录所有 SQL | `db/__init__.py:19` |
| 9 | 无 LLM 调用重试/退避/超时机制 | `llm_tavily.py`, `assistant.py:39` |
| 10 | 无限重试循环 (`while True`) | `assistant.py:39` |
| 11 | 无速率限制 | `api/system_mgt/user_views.py:46` |
| 12 | `passenger_id` 硬编码 | `graph_gradio.py:130`, `graph_schemas.py:12` |
| 13 | 白名单 `re.match` 不锚定 | `middlewares.py:32`, `docs_oauth2.py:41` |
| 14 | JWT 令牌无黑名单/撤销 | `utils/jwt_utils.py` |
| 15 | MemorySaver 不持久化 | `graph_gradio.py:109` |

### 1.3.3 P2 中风险 (10 项)

| # | 问题 |
|---|------|
| 16 | 3 路图定义重复 (`graph_gradio.py` / `finally_graph.py` / `第三个流程图.py`) |
| 17 | 子图构建器 76% 重复模板代码 (`build_child_graph.py`) |
| 18 | 3 个历史版本文件为死代码 |
| 19 | `api/__init__.py` 含测试垃圾代码 |
| 20 | 提示词模板中 `time=datetime.now()` 在模块导入时固化 |
| 21 | `draw_png.py` 静默吞掉所有异常 |
| 22 | 日志仅控制台，文件日志被注释 |
| 23 | `route_primary_assistant` 抛出 `ValueError("无效的路由")` 使会话崩溃 |
| 24 | 无结构化异常体系 |
| 25 | 酒店/租车/旅行工具无身份验证 |

---

# 第二部分: 目标架构

## 2.1 架构决策 (ADR)

| ADR | 决策 | 理由 |
|-----|------|------|
| ADR-1 | **移除 Gradio，仅保留 FastAPI** | 生产环境不需要 Gradio UI |
| ADR-2 | **切换到云端 LLM** | 通过 Provider 抽象层支持 OpenAI/DeepSeek 切换 |
| ADR-3 | **统一到 MySQL (业务) + PostgreSQL (Agent 记忆)** | 业务数据 MySQL，LangGraph Checkpoint + Store 用 PostgreSQL |
| ADR-4 | **Docker Compose → K8s 预留** | 起步 Docker Compose，架构支持后续迁移 |
| ADR-5 | **pydantic-settings 替代 Dynaconf** | 类型安全，`.env` 支持，FastAPI 生态兼容 |
| ADR-6 | **Poetry 替代裸 pip** | 依赖锁定、确定性构建 |
| ADR-7 | **保留 Supervisor 模式 (增强 + 可扩展)** | 当前 4 Agent 在 Supervisor 甜区 (2-5)；4→8+ Agent 时演进为分层监督 (Root → Team Lead → Specialist)；Agent Registry 支持动态注册 |
| ADR-8 | **六层分层设计** | 治理横切、表现/编排/Agent/能力/基础纵向分层 |
| ADR-9 | **Milvus 分布式模式 (50TB 向量)** | 50TB 量级唯一验证方案 |
| ADR-10 | **MinIO 分布式存储 (50TB 文档)** | S3 兼容，纠删码，生命周期管理 |
| ADR-11 | **意图分类替代 LLM 路由 (P0)** | 轻量分类器 (Haiku/Flash, 40ms) 处理 80% 路由 → 延迟 -2~3s，成本 -90% |
| ADR-12 | **并行 Fan-out 多领域请求 (P1)** | LangGraph Send API → 航班+酒店+租车同时查询 → 延迟 -55% |
| ADR-13 | **计划-执行分离 (P2)** | 仅 3+ 领域复合任务触发 Planner → 任务完成率 +40-70%，Plan 阶段 ~3000 Token 开销 |

## 2.2 六层分层架构

```
┌──────────────────────────────────────────────────────────────┐
│                                                               │
│  Layer 6:  治理层 (Governance)         ← 横切所有层           │
│  ────────────────────────────────────                         │
│  评估体系 · 护栏系统 · 幻觉检测 · Prompt 管理 ·              │
│  成本管理 · 反馈闭环 · 合规审计                               │
│                                                               │
├──────────────────────────────────────────────────────────────┤
│                                                               │
│  Layer 5:  表现层 (Presentation)                              │
│  ──────────────────────────────                               │
│  FastAPI 路由 · WebSocket 流式 · Schema 校验 · Session 管理   │
│                                                               │
├──────────────────────────────────────────────────────────────┤
│                                                               │
│  Layer 4:  编排层 (Orchestration)                             │
│  ────────────────────────────────                             │
│  State 定义 · StateGraph 拓扑 · 路由决策 · Handoff 协议 ·     │
│  降级策略 · 多轮澄清 · 人机交互中断                            │
│                                                               │
├──────────────────────────────────────────────────────────────┤
│                                                               │
│  Layer 3:  Agent 层 (Agent)                                   │
│  ────────────────────────────                                 │
│  Prompt 模板 · LLM 绑定 · 工具选择 · 多模型路由 · Token 预算   │
│                                                               │
├──────────────────────────────────────────────────────────────┤
│                                                               │
│  Layer 2:  能力层 (Capability)                                │
│  ─────────────────────────────                                │
│  Tool 定义 · 参数校验 · 业务逻辑 · 审计 · 错误标准化          │
│                                                               │
├──────────────────────────────────────────────────────────────┤
│                                                               │
│  Layer 1:  基础层 (Foundation)                                │
│  ─────────────────────────────                                │
│  LLM Provider · 记忆存储 · 向量检索 · 缓存 · 对象存储 ·      │
│  数据库连接池 · 消息队列                                       │
│                                                               │
└──────────────────────────────────────────────────────────────┘
```

### 各层职责边界

| 层 | 职责 | 不应做的事 | 变更频率 | 负责人 |
|----|------|-----------|---------|--------|
| L6 治理 | 评估、护栏、成本核算、合规 | 不应干预正常业务逻辑 | 低 | 平台团队 |
| L5 表现 | HTTP 协议适配、流式输出、验证 | 不应包含 Agent 逻辑 | 低 | 后端团队 |
| L4 编排 | 图拓扑、路由规则、中断处理 | 不应写 Prompt 内容 | 中 | Agent 架构师 |
| L3 Agent | Prompt 管理、工具选择策略 | 不应直接操作数据库 | **高** | Prompt 工程师 |
| L2 能力 | 原子工具实现、数据校验 | 不应做路由决策 | 中 | 后端团队 |
| L1 基础 | 连接池、存储引擎、LLM 调用 | 不感知业务 | 低 | 平台/DevOps |

## 2.3 目标项目结构

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
│   │   └── logging.py            # JSON 结构化日志
│   ├── middleware/                # 中间件层
│   │   ├── __init__.py
│   │   ├── auth.py               # JWT 认证中间件
│   │   ├── cors.py               # CORS 配置
│   │   ├── rate_limit.py         # 速率限制 (slowapi)
│   │   └── request_id.py         # 请求追踪 ID
│   ├── api/                      # API 路由
│   │   ├── __init__.py
│   │   ├── deps.py               # FastAPI 依赖注入
│   │   └── v1/                   # API v1
│   │       ├── __init__.py
│   │       ├── router.py         # 主路由聚合
│   │       ├── auth.py           # 认证端点
│   │       ├── users.py          # 用户 CRUD
│   │       ├── graph.py          # 多智能体对话
│   │       └── health.py         # 健康检查
│   ├── schemas/                  # Pydantic 模型
│   │   ├── __init__.py
│   │   ├── user.py
│   │   ├── graph.py
│   │   └── common.py
│   ├── services/                 # 业务服务层
│   │   ├── __init__.py
│   │   ├── auth_service.py
│   │   ├── user_service.py
│   │   └── graph_service.py
│   ├── graph/                    # LangGraph 多智能体系统
│   │   ├── __init__.py
│   │   ├── state.py              # State TypedDict
│   │   ├── graph.py              # 图构建 (主图 + 参数化子图工厂)
│   │   ├── routing.py            # 路由函数
│   │   ├── registry.py           # Agent 注册表 (8+ Agent 时启用)
│   │   ├── interrupts.py         # 中断处理
│   │   ├── handoff.py            # Agent 间通信协议
│   │   ├── lifecycle.py          # 子图生命周期
│   │   ├── fallback.py           # 降级策略链
│   │   ├── agents/               # Agent 定义
│   │   │   ├── __init__.py
│   │   │   ├── base.py           # Agent 基类
│   │   │   ├── classifier.py     # 意图分类器 (Haiku/Flash)
│   │   │   ├── primary.py        # 主 Agent (保留: 降级路由 + 复杂意图)
│   │   │   ├── flight.py         # 航班 Agent
│   │   │   ├── hotel.py          # 酒店 Agent
│   │   │   ├── car_rental.py     # 租车 Agent
│   │   │   ├── excursion.py      # 旅行 Agent
│   │   │   ├── planner.py        # Planner Agent (计划生成)
│   │   │   ├── critic.py         # Critic Agent (结果验证)
│   │   │   ├── router.py         # 多模型路由
│   │   │   ├── evaluator.py      # Agent 自评估
│   │   │   └── prompts/          # Prompt 仓库 (版本化管理)
│   │   │       ├── __init__.py
│   │   │       ├── primary.py
│   │   │       ├── flight.py
│   │   │       ├── hotel.py
│   │   │       ├── car_rental.py
│   │   │       └── excursion.py
│   │   ├── tools/                # Tool 定义
│   │   │   ├── __init__.py
│   │   │   ├── business/         # 业务工具
│   │   │   │   ├── flights.py
│   │   │   │   ├── hotels.py
│   │   │   │   ├── car_rentals.py
│   │   │   │   └── excursions.py
│   │   │   ├── knowledge/        # 知识工具
│   │   │   │   ├── policy.py     # RAG 政策查询
│   │   │   │   └── city_mapper.py
│   │   │   ├── system/           # 系统工具
│   │   │   │   ├── escalation.py
│   │   │   │   └── clarification.py
│   │   │   └── handler.py        # ToolNode + fallback
│   │   ├── models.py             # 路由/委托 Pydantic 模型
│   │   └── guardrails/           # 护栏
│   │       ├── __init__.py
│   │       ├── input_guard.py    # 输入过滤
│   │       ├── output_guard.py   # 输出过滤
│   │       └── config/           # NeMo Guardrails 配置
│   ├── db/                       # 数据访问层
│   │   ├── __init__.py
│   │   ├── engine_mysql.py       # MySQL 连接池
│   │   ├── engine_pg.py          # PostgreSQL 连接池
│   │   ├── models/               # ORM 模型
│   │   │   ├── __init__.py
│   │   │   ├── user.py
│   │   │   ├── flight.py
│   │   │   ├── hotel.py
│   │   │   ├── car_rental.py
│   │   │   ├── excursion.py
│   │   │   ├── city.py
│   │   │   └── audit.py
│   │   └── repositories/         # Repository 层
│   │       ├── __init__.py
│   │       ├── base.py
│   │       ├── user.py
│   │       ├── flight.py
│   │       ├── hotel.py
│   │       └── audit.py
│   ├── infrastructure/           # 基础层
│   │   ├── __init__.py
│   │   ├── llm/
│   │   │   ├── base.py           # AbstractLLMProvider
│   │   │   ├── openai.py
│   │   │   └── deepseek.py
│   │   ├── vector/
│   │   │   └── milvus.py
│   │   ├── storage/
│   │   │   └── minio.py
│   │   ├── cache/
│   │   │   ├── exact.py          # L1 精确缓存
│   │   │   └── semantic.py       # L2 语义缓存
│   │   └── queue/
│   │       ├── celery_app.py
│   │       └── tasks.py
│   ├── governance/               # 治理层横切
│   │   ├── __init__.py
│   │   ├── evaluator.py          # Agent 评估
│   │   ├── guardrails.py         # 护栏管理
│   │   ├── hallucination.py      # 幻觉检测
│   │   ├── cost.py               # 成本管理
│   │   ├── provenance.py         # 决策溯源
│   │   ├── confidence.py         # 置信度估计
│   │   └── feedback.py           # 反馈闭环
│   └── utils/
│       ├── __init__.py
│       └── city_mapper.py
├── migrations/                   # Alembic 数据库迁移
│   ├── alembic.ini
│   └── versions/
├── tests/                        # 测试
│   ├── __init__.py
│   ├── conftest.py
│   ├── unit/
│   │   ├── test_graph_state.py
│   │   ├── test_graph_routing.py
│   │   ├── test_tools.py
│   │   ├── test_security.py
│   │   └── test_guardrails.py
│   └── integration/
│       ├── test_api_auth.py
│       ├── test_api_graph.py
│       ├── test_graph_flow.py
│       └── test_rag_pipeline.py
├── data/                         # 静态数据
│   ├── travel_new.sqlite         # 初始数据 (迁移后废弃)
│   └── order_faq.md              # RAG 文档源
├── scripts/                      # 运维脚本
│   ├── init_db.py                # 数据库初始化
│   ├── seed_data.py              # 种子数据
│   └── migrate_sqlite_to_mysql.py
├── docker/                       # Docker 配置
│   ├── Dockerfile
│   ├── docker-compose.yml
│   ├── nginx.conf
│   └── prometheus.yml
├── .env.example                  # 环境变量模板
├── .env                          # 本地环境变量 (不提交)
├── .gitignore
├── pyproject.toml                # Poetry 配置
├── Makefile                      # 常用命令
└── README.md
```

---

# 第三部分: 各层详细设计

## 3.1 Layer 1: 基础层

### 3.1.1 职责

提供所有上层依赖的基础设施能力。上层通过依赖注入获取资源，不直接实例化连接。

### 3.1.2 LLM Provider 抽象

**设计目标**: 支持 OpenAI / DeepSeek 及未来模型切换，一套接口。

**接口设计**:
```
AbstractLLMProvider
  ├── get_chat_model() → BaseChatModel
  │    配置: model, temperature, max_retries, timeout
  ├── get_embedding_model() → Embeddings
  └── health_check() → bool

OpenAIProvider     → ChatOpenAI + OpenAIEmbeddings
DeepSeekProvider   → ChatOpenAI(base_url="https://api.deepseek.com")
```

**多模型路由**: 提供 `ModelRouter` 根据查询复杂度选择不同模型 (详见 Layer 3)。

### 3.1.3 数据库连接池

**MySQL (业务数据)**:
```
MySQL (ProxySQL 读写分离):
  ├── 主库 (写入): 连接池 20 连接
  └── 从库 (读取): 连接池 40 连接
  参数: pool_pre_ping=True, pool_recycle=3600
  echo=settings.DEBUG (生产 False)
```

**PostgreSQL (Agent 记忆)**:
```
PostgreSQL (PgBouncer 连接池 → Patroni HA 集群):
  ├── langgraph 数据库: Checkpoint + Store
  └── PgBouncer: pool_mode=transaction, pool_size=64
```

### 3.1.4 缓存层

四级缓存模型:

| 级别 | 位置 | 命中条件 | 延迟 | TTL |
|------|------|---------|------|-----|
| L1 | 应用内存 | MD5(query+model+top_k) 精确匹配 | ~1ms | 1h |
| L2 | Redis | cosine_similarity > 0.92 语义匹配 | ~50ms | 1h |
| L3 | Redis | 相同 embedding → 相同检索结果 | ~100ms | 7d |
| L4 | 全量管线 | Embedding → VectorDB → LLM | ~2-8s | N/A |

**缓存失效策略**: 命名空间版本化。模型/文档变更时递增版本号，旧 key 通过 TTL 自然过期。

**成本节省预估**: 综合 L1+L2 命中率约 40-50%，可降低 60-68% LLM 调用量。

### 3.1.5 对象存储 (MinIO)

```
MinIO 分布式集群 (8-16 节点):
  ├── documents/raw/       # 原始文档 (30天后转 WARM)
  ├── documents/parsed/    # 解析后结构化内容
  ├── vectors/             # 向量索引快照 (365天过期)
  ├── temp/                # 临时上传 (7天过期)
  └── backups/             # 系统备份

存储分层:
  HOT  (NVMe SSD, <1ms)  → 近 30 天文档
  WARM (SATA SSD, <5ms)  → 30-90 天文档
  COLD (HDD, <50ms)      → 90 天+ 归档
```

### 3.1.6 消息队列

```
Celery + Redis (当前):
  ├── urgent_reindex 队列 (最高优先级)
  ├── pdf_deep_parse 队列
  ├── office_parse 队列
  └── batch_ingest 队列 (最低优先级)

预留: Kafka 升级路径 (当吞吐量超过 Celery 处理能力时)
```

---

## 3.2 Layer 2: 能力层

### 3.2.1 职责

定义可被 Agent 调用的原子工具。每个工具遵循统一契约。

### 3.2.2 工具分类

```
app/graph/tools/
  ├── business/             # 业务工具
  │   ├── flights.py        # 航班搜索/改签/取消
  │   ├── hotels.py         # 酒店搜索/预订/取消
  │   ├── car_rentals.py    # 租车搜索/预订/取消
  │   └── excursions.py     # 旅行搜索/预订/取消
  ├── knowledge/            # 知识检索工具
  │   ├── policy.py         # RAG 政策查询
  │   └── city_mapper.py    # 城市名称解析
  └── system/               # 系统工具
      ├── escalation.py     # 升级到主 Agent / 转人工
      └── clarification.py  # 请求用户澄清
```

### 3.2.3 工具统一契约

```python
@tool
def book_hotel(
    hotel_id: int,
    runtime: ToolRuntime[UserContext, State],
) -> ToolResult:
    """
    预订酒店。所有写操作工具必须接受 ToolRuntime 进行身份验证和审计。

    Args: hotel_id: 要预订的酒店 ID
    Returns: ToolResult {status, message, data}
    """
    # 1. 身份验证 + 审计
    user_id = runtime.context.user_id
    _audit("book_hotel", user_id, {"hotel_id": hotel_id})

    # 2. 执行业务逻辑
    try:
        repo = HotelRepository()
        result = repo.book(hotel_id, user_id)
        return ToolResult(status="success", message=f"酒店 {hotel_id} 预订成功")
    except Exception as e:
        return ToolResult(status="error", message=str(e))
```

### 3.2.4 工具身份验证矩阵

| 工具 | 操作类型 | 身份要求 | 备注 |
|------|---------|---------|------|
| `search_flights` | 读 | 无 (公开查询) | |
| `fetch_user_flight_information` | 读 | 需 passenger_id | 仅查本人 |
| `update_ticket_to_new_flight` | 写 | 需 passenger_id + 所有权验证 | 人机确认 |
| `cancel_ticket` | 写 | 需 passenger_id + 所有权验证 | 人机确认 |
| `search_hotels` | 读 | 无 | |
| `book_hotel` | 写 | 需 user_id (审计) | |
| `cancel_hotel` | 写 | 需 user_id (审计) | |
| `lookup_policy` | 读 | 无 | RAG 检索 |

---

## 3.3 Layer 3: Agent 层

### 3.3.1 职责

管理 Prompt 模板、LLM 工具绑定、输出解析。与编排层解耦——编排层定义拓扑，Agent 层定义"怎么回答"。

### 3.3.2 Agent 基类

```python
class BaseAgent:
    """统一提供重试、超时、护栏钩子、评估调度"""

    def __init__(self, runnable, guardrail=None, max_retries=3, timeout=60):
        self.runnable = runnable
        self.guardrail = guardrail
        self.max_retries = max_retries
        self.timeout = timeout

    def invoke(self, state, config):
        # 1. 护栏: 输入检查 (Layer 6 注入)
        if self.guardrail:
            self.guardrail.check_input(state)

        # 2. 带指数退避和超时的 LLM 调用
        for attempt in range(self.max_retries):
            try:
                with timeout_context(self.timeout):
                    result = self.runnable.invoke(state)
                if self._is_valid_result(result):
                    break
            except TimeoutError:
                if attempt == self.max_retries - 1: raise
            except Exception as e:
                if attempt == self.max_retries - 1: raise
                time.sleep(2 ** attempt)
            # 空内容重试
            state = self._append_retry_prompt(state)

        # 3. 护栏: 输出检查
        if self.guardrail:
            self.guardrail.check_output(result)

        # 4. 内嵌评估 (异步，不阻塞响应)
        self._schedule_evaluation(state, result)

        return {"messages": result}
```

### 3.3.3 Prompt 分离

Prompt 从代码中抽出到独立 `prompts/` 目录，支持版本化:

```
# agents/prompts/primary.py — 纯 Prompt 定义
PRIMARY_SYSTEM_PROMPT = """
您是携程瑞士航空公司的客户服务助理。
您的主要职责是搜索航班信息和公司政策以回答客户的查询。
如果客户请求更新或取消航班、预订租车、预订酒店或获取旅行推荐，
请通过调用相应的工具将任务委派给合适的专门助理。
...
当前用户的航班信息:
<Flights>
{user_info}
</Flights>
当前时间: {time}.
"""

# agents/primary.py — Agent 逻辑
class PrimaryAgent(BaseAgent):
    def __init__(self, llm_provider):
        prompt = ChatPromptTemplate.from_messages([
            ("system", PRIMARY_SYSTEM_PROMPT),
            ("placeholder", "{messages}"),
        ]).partial(time=lambda: datetime.now())  # 运行时动态注入

        tools = [ToFlightBookingAssistant, ToBookCarRental,
                 ToHotelBookingAssistant, ToBookExcursion,
                 lookup_policy, search_flights]

        runnable = prompt | llm_provider.get_chat_model().bind_tools(tools)
        super().__init__(runnable=runnable, max_retries=3)
```

### 3.3.4 多模型路由

根据查询复杂度选择不同模型:

```
用户查询 → 复杂度分类器 (8 个信号)
  ├── 简单 (70%): gpt-4.1-mini    ($0.05/$0.20 per M tokens)
  ├── 中等 (25%): claude-haiku-4.5 ($1.00/$5.00)
  └── 复杂 (5%):  claude-sonnet-4.6 ($3.00/$15.00)

8 个分类信号: 消息长度、对话深度、工具使用模式、推理深度、
              领域特异性、行动风险等级、语言复杂度、代码存在性
```

### 3.3.5 意图分类器 (替代 LLM 路由)

**设计目标**: 用轻量分类器替代 Primary Agent 的 LLM 路由调用，降低延迟和成本。

**为什么不用 LLM 路由**: 每次路由调一次 LLM (~1s, ~$0.01)，且概率性。用户说"帮我查航班"的意图是明确的——不需要 GPT-4 来判断。

**分类器设计**:

```
意图分类器 (Haiku/Flash, 40ms, $0.000025/次)
  输入: 用户消息 + 对话上下文
  输出: {intent: "flight"|"hotel"|"car_rental"|"excursion"|"multi_domain"|"clarification",
         confidence: 0.95,
         entities: {departure: "北京", arrival: "苏黎世", date: "2026-04-30"}}

决策逻辑:
  confidence >= 0.85 → 确定性路由 (跳过 LLM 路由)
  confidence < 0.85  → 回退 LLM 路由 + 请求用户澄清
  intent = "multi_domain" → 并行 Fan-out
  intent = "clarification" → 追问缺失信息
```

**成本对比**:

| 方式 | 延迟 | 成本/次 | 月成本 (100K 请求) |
|------|------|---------|-------------------|
| LLM 路由 (GPT-4o) | ~1s | ~$0.0025 | $250 |
| 分类器 (Haiku) | ~40ms | ~$0.000025 | $2.50 |
| **节省** | **-96%** | **-99%** | **-$247.50** |

### 3.3.6 Planner Agent (计划-执行分离)

**适用范围**: 仅当请求涉及 3+ 领域或含依赖关系时触发。简单单领域请求不经过此路径。

**设计**:

```
用户: "帮我规划下周三去苏黎世的完整行程"

  Planner Agent (Sonnet/4o, ~3000 Token):
    输入: 用户请求 + 上下文
    输出: {
      steps: [
        {id: 1, domain: "flight", action: "search", depends_on: []},
        {id: 2, domain: "hotel", action: "search", depends_on: [1]},
        {id: 3, domain: "excursion", action: "search", depends_on: []},
        {id: 4, domain: "synthesize", action: "recommend", depends_on: [1,2,3]}
      ]
    }

  Executor → 按依赖关系执行:
    Wave 1 (并行): Step 1 + Step 3
    Wave 2 (串行): Step 2 (依赖 Step 1 的到达时间)
    Wave 3 (汇总): Step 4

好处: 全局视角、无遗漏、可追踪
代价: 多一次 LLM 调用 (~3000 Token)
触发条件: 分类器判定 intent="multi_domain" 且涉及 >= 3 个领域
```

---

## 3.4 Layer 4: 编排层

### 3.4.1 职责

定义图拓扑、路由逻辑、人机交互中断、子图生命周期。不写 Prompt，不实现工具。

### 3.4.2 State 定义

```python
class State(TypedDict):
    # 对话核心
    messages: Annotated[list[AnyMessage], add_messages]
    summary: str  # 对话摘要 (SummarizationNode 输出)

    # 用户身份 (从 L5 表现层注入)
    user_id: int
    username: str
    passenger_id: str

    # 用户上下文
    user_info: dict  # 航班信息 + 用户偏好

    # 子图路由栈
    dialog_state: list[str]

    # 决策智能 (Layer 6 治理层横切)
    decision_path: list[DecisionNode]  # 决策溯源
    confidence_scores: dict            # 置信度
    guardrail_flags: list              # 护栏标记

    # 多轮澄清
    clarification_needed: bool
    collected_slots: dict  # {departure: "北京", arrival: null}
```

### 3.4.3 图拓扑 (增强版)

```
START → load_user_memory → summarize
  │
  ▼
intent_classifier (Haiku, 40ms)
  │
  ├── single_domain (80%) ──→ 确定性路由 ──→ 对应子 Agent
  │
  ├── multi_domain (15%) ──→ Fan-out (Send API)
  │     ├─ flight_agent (并行)
  │     ├─ hotel_agent (并行)
  │     └─ car/excursion_agent (并行)
  │            │
  │            ▼
  │     fan_in_merge (汇总结果)
  │
  ├── complex (5%, 3+ domains) ──→ planner_agent ──→ executor (按计划执行)
  │                                            │
  │                                    各子 Agent (按依赖关系)
  │                                            │
  │                                     critic_agent (验证结果)
  │
  └── low_confidence ──→ fallback_llm_router ──→ 对应子 Agent 或请求澄清
       │
       ▼
  各子 Agent 内部:
    enter_xxx → xxx_agent → route → safe_tools | sensitive_tools[中断] | leave_skill
       │                          │
       └──────────────────────────┘
                  │
            子 Agent 间 P2P Handoff (条件边):
              flight_agent → hotel_agent (当 flight_agent 的 tool_call 包含 ToHotelBookingAssistant)
                  │
                  ▼
            extract_memories → END
```

**关键变化 vs 当前**:

| 变化 | 当前 | 增强后 |
|------|------|--------|
| 首次路由 | LLM tool_call (~1s) | 分类器 (40ms) |
| 多领域请求 | 串行 | Fan-out 并行 (Send API) |
| 复合任务 | 无规划 | Planner → Executor |
| 子 Agent 通信 | 仅通过 Primary | P2P Handoff (条件边) |
| 结果验证 | 无 | Critic Agent |

### 3.4.3a 扩展性: 8+ Agent 分层监督架构

**触发条件**: 当子 Agent 数量超过 6-8 个时，单层 Supervisor 面临以下瓶颈:
- 分类器需要从 8+ 个候选中选择 → 准确率下降
- Primary Agent 的工具列表过长 → LLM 工具选择出错率上升
- 所有 Agent 共享一个 State → 上下文膨胀

**演进路径**: 四层监督金字塔

```
                         ┌─────────────────────┐
                         │   Root Supervisor    │  ← 仅路由，不执行业务
                         │   (Sonnet/4o)        │
                         └──────────┬──────────┘
                                    │
          ┌─────────────────────────┼─────────────────────────┐
          │                         │                         │
  ┌───────▼───────┐       ┌────────▼────────┐       ┌───────▼───────┐
  │ Travel Team   │       │ Accommodation    │       │ Services Team │
  │ Lead          │       │ Team Lead        │       │ Lead          │
  │ (Flight+Trans)│       │ (Hotel+Resort)   │       │ (Car+Activity)│
  └───────┬───────┘       └────────┬────────┘       └───────┬───────┘
          │                        │                        │
   ┌──────┼──────┐          ┌──────┼──────┐          ┌──────┼──────┐
   ▼      ▼      ▼          ▼      ▼      ▼          ▼      ▼      ▼
 Flight Transit Airport   Hotel  Resort  B&B     Car    Tour   Dining
 Agent  Agent  Agent     Agent  Agent  Agent    Rental Guide  Agent
```

**分层原则**:

| 层 | 数量 | 职责 | 模型选择 |
|----|------|------|---------|
| Root Supervisor | 1 | 顶层路由: 判断用户意图属于哪个团队 | Sonnet/4o |
| Team Lead | 3-5 | 团队内路由: 判断具体交给哪个专家 | Haiku/Flash |
| Specialist Agent | 每个团队 2-4 | 执行具体业务逻辑 | 按复杂度路由 |

**分类器演进**:

```
4 Agent 阶段:    单级分类器 → 直接从 4 个候选中选
8+ Agent 阶段:   两级分类 → L1: 团队 (3-5 类) → L2: 团队内专家 (2-4 类)
```

**Agent 注册表** (动态管理):

```
Agent Registry (PostgreSQL 表):
  agent_id | name | team | capabilities | tools[] | model | status

当 Agent 数量 >8 时，路由逻辑从硬编码 if/elif 切换为:
  1. 查询 Registry 获取活跃 Agent 列表
  2. 两级分类: L1 选 team → L2 选 agent
  3. 动态构建工具列表

好处: 新增 Agent 无需修改路由代码，注册即可生效
```

**当前 4 Agent 架构已为 8+ 预留**:
- 现有的域名分离 (Flight/Hotel/Car/Excursion) 天然对应未来的团队分组
- Primary Agent → 未来退化为 Root Supervisor
- 新增 Agent 只需在 Registry 注册 + 实现 BaseAgent 接口

### 3.4.4 Handoff 协议

标准化的子 Agent 间通信:

```
Handoff 请求 (主 → 子):
  {type: "handoff", from: "primary", to: "flight_agent",
   context: {user_intent: "改签航班", relevant_info: "..."}}

Handoff 响应 (子 → 主):
  {type: "handoff_response", from: "flight_agent",
   status: "completed" | "escalated" | "needs_clarification",
   result: "改签成功", context: {...}}
```

### 3.4.5 降级策略链

```
用户请求
  → LLM 调用成功? → 正常响应
  → LLM 失败 → 语义缓存命中? → 返回缓存 (标注"可能不完全准确")
  → 缓存未命中 → 规则引擎匹配? → 返回预定义响应
  → 无匹配 → 转人工 / 兜底回复
```

### 3.4.6 参数化子图工厂

消除 76% 重复代码:

```
build_sub_graph(builder, config):
  config = {
    entry_name, assistant_name,
    safe_tools_name, sensitive_tools_name,
    dialog_state, runnable,
    safe_tools[], sensitive_tools[]
  }
  → 自动创建: 入口节点、Agent 节点、工具节点、路由边、leave_skill
```

---

## 3.5 Layer 5: 表现层

### 3.5.1 职责

HTTP 协议适配、流式输出、请求校验、Session 管理。不包含 Agent 逻辑。

### 3.5.2 API 端点

```
认证:
  POST   /api/v1/auth/register       # 用户注册
  POST   /api/v1/auth/login          # 用户登录 (JSON)
  POST   /api/v1/auth/token          # OAuth2 表单 (Swagger)
  POST   /api/v1/auth/refresh        # 刷新 Token
  POST   /api/v1/auth/logout         # 登出

用户管理:
  GET    /api/v1/users               # 用户列表 (分页)
  GET    /api/v1/users/{user_id}     # 用户详情
  PATCH  /api/v1/users/{user_id}     # 更新用户
  DELETE /api/v1/users               # 批量删除

多智能体对话:
  POST   /api/v1/graph/chat          # 发起对话 (支持 SSE 流式)
  GET    /api/v1/graph/sessions      # 用户会话列表
  GET    /api/v1/graph/sessions/{id} # 会话详情
  DELETE /api/v1/graph/sessions/{id} # 删除会话

系统:
  GET    /api/v1/health              # 健康检查
  GET    /api/v1/metrics             # Prometheus 指标
```

### 3.5.3 流式输出 (SSE)

```
POST /api/v1/graph/chat
  → SSE events:
    event: thinking     → {agent, status}
    event: tool_call    → {tool, args}
    event: interrupt    → {message, requires_confirmation}
    event: token        → {content}
    event: done         → {session_id, cost}
```

### 3.5.4 从 JWT 到 Runtime Context

```python
# graph_views.py
def execute_graph(request: Request, obj_in: BaseGraphSchema):
    # 1. 从 JWT Middleware 获取已认证用户
    raw = request.state.username       # "1:alice"
    user_id_str, username = raw.split(':', 1)
    user_id = int(user_id_str)

    # 2. 查找 user → passenger 映射
    passenger_id = resolve_passenger(user_id)

    # 3. 构建 Runtime Context
    context = UserContext(
        user_id=user_id,
        username=username,
        passenger_id=passenger_id,
    )

    # 4. 线程隔离: thread_id = user_{id}:{uuid}
    thread_id = f"user_{user_id}:{uuid.uuid4()}"

    # 5. 调用编排层
    events = graph.stream(
        input={"messages": [HumanMessage(content=user_input)]},
        config={"configurable": {"thread_id": thread_id}},
        context=context,
    )
```

### 3.5.5 错误响应格式

```json
{
  "error": {
    "code": "LLM_SERVICE_UNAVAILABLE",
    "message": "AI 服务暂时不可用",
    "request_id": "req_abc123",
    "timestamp": "2026-04-28T10:30:00Z"
  }
}
```

---

## 3.6 Layer 6: 治理层

治理层是横切面，不单独部署，通过钩子和中间件注入到各层。

### 3.6.1 Agent 评估体系

**三层评估矩阵**:

```
类型 1: 行为检查 (无需标准答案)
  语气合规、格式正确、无禁止内容
  适用于每次对话

类型 2: 上下文检查 (需要检索上下文)
  输出是否基于检索文档 (忠实性)
  Agent 是否调用了正确工具
  捕获"调对了工具但编造了结果"

类型 3: 标准答案检查 (需要标注数据)
  预期工具调用序列
  输出与参考答案匹配
  用于 CI/CD 回归门禁
```

**核心指标**:

| 指标 | 告警阈值 | 测量工具 |
|------|---------|---------|
| 忠实性 (Faithfulness) | < 0.85 | LangSmith / RAGAS |
| 回答相关性 | < 0.80 | LangSmith |
| 工具选择准确率 | < 0.90 | 自定义 Evaluator |
| 轨迹效率 | > 2.0x 理想步骤数 | LangSmith Trajectory |

**CI/CD 评估门禁**:
```
PR → 离线评估 → 得分 >= 0.85 → 合并
               得分 < 0.85  → 阻断 + 通知
```

### 3.6.2 五层护栏

```
Layer 1: 快速确定性检查 (毫秒级)
  工具: regex + Presidio
  覆盖: PII 检测、敏感词过滤、格式校验

Layer 2: 小模型分类 (百毫秒级)
  工具: Llama Guard / NeMo self_check
  覆盖: 内容安全、越狱检测、主题控制

Layer 3: Agent 执行护栏 (内嵌)
  工具: NeMo GuardrailsMiddleware (每个节点)
  覆盖: 工具调用权限、参数校验

Layer 4: 输出验证 (秒级)
  工具: 幻觉检测 + 事实性校验
  覆盖: 生成内容 vs 检索文档一致性

Layer 5: 人机协同 (最终防线)
  工具: LangGraph interrupt()
  覆盖: 高风险操作需用户确认
```

**严重度处理**:

| 严重度 | 类型 | 动作 |
|--------|------|------|
| 4 | 与上下文矛盾 | **阻断**, 替换为免责声明 |
| 3 | 虚构信息 | **阻断** |
| 2 | 不可验证 | 软处理: 标注置信度, 留待审核 |
| 1 | 推测性表述 | 记录日志, UI 标注 |

### 3.6.3 幻觉检测

**四层检测栈**:
1. **忠实性检查**: 输出 → 原子声明 → NLI 逐条验证
2. **矛盾检查**: 输出是否主动与检索文档矛盾
3. **引用验证**: 验证每个引用来源确实支撑对应声明
4. **Token 级检测**: 逐 Token 标注有支撑/无支撑

**设计要点**:
- NLI 模型用于生产 (快速/准确/廉价)，LLM-as-Judge 用于高精度场景
- 不确定时不回答 (Abstention) 优于给出错误答案

### 3.6.4 Prompt 版本化管理

```
开发环境: prompt = hub.pull("org/rag-answer-prompt")  # 最新
生产环境: prompt = hub.pull("org/rag-answer-prompt:abc123")  # 锁定 commit

变更流: Prompt 修改 → CI 离线评估 → Staging 在线评估 → 提升到 Production 标签
回滚: 改 hash → 重启进程 (无需代码部署)
```

### 3.6.5 成本管理

**多模型路由** (详见 L3 Agent 层): 简单→廉价模型, 复杂→昂贵模型, 综合节省 60-80%。

**语义缓存** (详见 L1 基础层): 精确 + 语义双层缓存，命中率 40-50%，节省 60-68% LLM 调用。

**Token 预算**:

| 维度 | 限制 |
|------|------|
| 单用户/日 | 100K tokens |
| 单会话 | 50K tokens |
| LLM 推理深度 | 16K tokens 上限 |
| 每日总预算告警 | 80% → Warning, 100% → 限流 |

**成本归因**: 每个 Agent 调用记录模型/Token/费用 → 按用户/会话/Agent/工具维度聚合 → Grafana 实时展示。

### 3.6.6 反馈闭环

```
生产对话日志
  ├── 用户反馈 (赞/踩) → 自动标注
  ├── 低分对话 → 人工审核队列
  └── 护栏触发 → 问题分类
         │
         ▼
  标注数据集更新
         │
         ▼
  每月 DSPy MIPROv2 自动优化 Prompt
         │
         ▼
  离线评估 → CI 门禁 → 灰度发布
```

---

# 第四部分: 核心子系统设计

## 4.1 RAG 系统

### 4.1.1 现状与目标

| 维度 | 现状 | 目标 |
|------|------|------|
| 向量存储 | numpy 内存数组 | Qdrant (\(\le\)10TB) / Milvus (50TB) |
| 文档分块 | `re.split("(?=\\n##)")` | MarkdownHeader + 中文 RecursiveCharacter |
| 嵌入计算 | 每次重启全量重算 | LangChain Indexing API 增量索引 |
| 嵌入模型 | OpenAI (硬编码 Key) | text-embedding-3-small → BGE-large-zh-v1.5 |
| 检索 | 暴力点积 top-k | 混合搜索 (Dense + BM25) + RRF 融合 |
| 重排序 | 无 | 预留 Cohere/BGE-Reranker (文档 >500 条触发) |
| 文档更新 | 需重启 | 增量: MD5 内容哈希变更检测 |

### 4.1.2 中文分块策略

| 参数 | 取值 | 理由 |
|------|------|------|
| 分隔符优先级 | `\n\n` → `\n` → `。！？` → `；` → `，、` | 中文无空格分隔，句末标点优先 |
| chunk_size | 512 字符 | 约 200-300 tokens，适配嵌入模型上下文 |
| chunk_overlap | 100 字符 (20%) | FAQ 政策条款前后引用多 |
| 双层分块 | MarkdownHeader + RecursiveCharacter | 保留标题元数据 + 语义完整性 |

### 4.1.3 Parent-Child 分块

```
父块 (1024-2048 tokens) → MinIO/PostgreSQL 存储 (无需嵌入)
  ├── 子块 1 (128-200 tokens) → 嵌入 → Milvus
  ├── 子块 2 (128-200 tokens) → 嵌入 → Milvus
  └── ...

检索流程: 匹配子块 → 查询 parent_id → 取父块 → 去重 → 返回 LLM
```

### 4.1.4 文档更新 (LangChain Indexing API)

```
变更检测: order_faq.md → MD5 哈希
  → 与 SQLRecordManager 记录比对
  → 仅处理新增/修改/删除的分块
  → 增量更新 Qdrant/Milvus
cleanup="incremental": 仅删除同一 source_id 的旧版本
```

### 4.1.5 LangGraph 集成

RAG 保持为 Agent Tool (非内联节点):
```
primary_assistant → 判断需要查政策 → 调用 lookup_policy tool
  → ToolNode 执行 → 检索结果注入对话上下文 → LLM 生成回答
```

---

## 4.2 记忆与检查点机制

### 4.2.1 三层记忆架构

```
Layer 1: 短期记忆 (Per-Turn)
  State.messages + SummarizationNode
  生命周期: 单次图执行
  摘要触发: >2048 tokens → 压缩为 256 token 摘要

Layer 2: 会话记忆 (Per-Session)
  PostgresSaver Checkpoint
  生命周期: 单次对话会话
  持久化: 每个节点执行后写入 PostgreSQL
  保留: TTL 30 天, 保留最近 20 checkpoint/thread

Layer 3: 长期记忆 (Cross-Session)
  PostgresStore
  生命周期: 跨会话持久
  内容: 用户偏好、历史行程、常用目的地
  更新: 每次对话结束后 LLM 提取
```

### 4.2.2 检查点后端选择

选择 **PostgresSaver** (LangGraph 官方) 而非 langgraph-checkpoint-mysql (社区):
- 官方维护 + 完整迁移系统
- 连接池 + 并发安全 + JSONB 索引
- pipeline 模式优化批量写入

### 4.2.3 对话摘要 (SummarizationNode)

```
对话 token 数 > 2048 → SummarizationNode 触发
  ├── 提取摘要 (max 256 tokens)
  ├── 合并旧摘要 + 新轮次
  └── 两条消息流: messages (完整) vs summarized_messages (LLM 输入)
```

### 4.2.4 检查点保留策略

| 策略 | 参数 |
|------|------|
| 时间 TTL | 30 天 |
| 数量限制 | 保留最近 20 个/thread |
| 提取优先 | GC 前提取关键信息到 Store |
| 定时执行 | 每日凌晨 CronJob |

### 4.2.5 对话生命周期

```
[发起] POST /chat (thread_id=null) → 创建 thread_id → 加载长期记忆
[每轮] SummarizationNode → Agent → 工具 → Checkpoint → 中断
[结束] extract_memories → 写入 PostgresStore → END
[恢复] GET /sessions → 选择 thread_id → PostgresSaver 恢复
```

---

## 4.3 跨 Agent 用户身份统一

### 4.3.1 身份注入链路

```
HTTP JWT → Middleware 解码 → request.state.username
  → API 层解析 user_id → 查 user→passenger 映射
  → 构建 UserContext → graph.stream(context=UserContext)
  → LangGraph Runtime 自动注入 Runtime[UserContext] 到所有节点
  → ToolRuntime[UserContext] 注入到所有工具
```

### 4.3.2 关键设计点

- 身份通过 `Runtime Context` 注入，**不写入 checkpoint** (避免 PII 泄漏)
- API 请求体中的 `passenger_id` 字段**移除**——身份只能从 JWT 派生
- 所有写操作工具强制接受 `ToolRuntime[UserContext]` 进行所有权验证
- `thread_id = "user_{id}:{uuid}"` 实现线程级多租户隔离

### 4.3.3 用户↔乘客映射

```sql
ALTER TABLE t_user ADD COLUMN passenger_id VARCHAR(50);
CREATE INDEX idx_user_passenger ON t_user(passenger_id);
```

### 4.3.4 审计追踪

```
audit_events 表 (MySQL 分区表):
  {event_type: "tool_call", user_id, passenger_id, tool_name,
   params (PII 脱敏), result_status, thread_id, timestamp}
```

---

## 4.4 城市映射数据库化

### 4.4.1 表设计

```sql
CREATE TABLE cities (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name_zh VARCHAR(50) NOT NULL,       -- 北京
    name_en VARCHAR(50) NOT NULL,       -- Beijing
    name_aliases JSON,                  -- ["北京市","Peking"]
    iata_code VARCHAR(5),               -- PEK
    country VARCHAR(50),                -- CN
    timezone VARCHAR(50),
    is_active BOOLEAN DEFAULT TRUE,
    INDEX idx_name_zh (name_zh),
    INDEX idx_name_en (name_en),
    INDEX idx_iata (iata_code)
);
```

### 4.4.2 查询策略

```
1. 应用内存 LRU Cache (maxsize=200, ttl=1h)
2. DB: WHERE name_zh=? OR name_en=? OR JSON_CONTAINS(aliases,?) OR iata_code=?
3. 返回标准化英文名称
```

---

## 4.5 文档处理管线

### 4.5.1 两阶段解析路由

```
文档输入 → 类型检测 (magic bytes/扩展名)
  ├── 原生 PDF → PyMuPDF4LLM (快速, 10-50x faster)
  ├── 扫描 PDF → MinerU + PaddleOCR (中文 OCR)
  ├── Office → Marker / Unstructured.io
  ├── HTML → 专用清洗器
  ├── 结构化数据 → Schema 感知序列化器
  └── 实时流 → 固定窗口分块器 (确定性)
```

### 4.5.2 分块策略矩阵

| 文档类型 | 分块策略 | 子块 | 父块 |
|---------|---------|------|------|
| 政策/法规 | 语义分块 | 200t | 1024t |
| 实时数据流 | 固定滑动窗口 | 256t | — |
| 表格密集 | 结构感知 | 逐表 | 整表 |
| 法律/合同 | 句子级 | 128t | 2048t |
| 历史归档 | 语义分块 | 200t | 1024t |

**关键原则**: 高频更新文档使用确定性分块；语义分块仅用于低频归档。

### 4.5.3 异步处理队列

```
Celery + Redis 分层队列:
  urgent_reindex (最高)  → 实时数据流
  pdf_deep_parse (高)    → PDF + OCR
  office_parse (中)      → Office
  batch_ingest (低)      → 批量全量重建
  retry_dlq (最低)       → 失败重试
```

---

## 4.6 分布式检索架构

### 4.6.1 Milvus 分布式拓扑

50TB 文档 (约 1-2 亿向量) 需要:

```
Milvus 集群:
  Proxy: 3-5 节点 (无状态, 可水平扩展)
  QueryNode: 8-16 节点, 128GB+ RAM (内存密集)
  DataNode: 3-6 节点 (IO 密集)
  IndexNode: 2-4 节点, 64GB+ RAM (CPU 密集)
  etcd: 元数据协调
  Pulsar/Kafka: 消息队列
  MinIO: 向量+索引持久化

分片配置: 4-8 分片 (创建后不可变更)
索引类型: IVF_SQ8 (内存效率与召回率平衡)
副本数: 3
```

### 4.6.2 检索漏斗

```
阶段 1: 稀疏检索 (粗过滤)
  相关文档聚类为粗粒度单元 → 亿级→万级 (减少 97%)

阶段 2: 密集检索 (中度过滤)
  粗粒度 → 文档级 → 万级→千级

阶段 3: 交叉编码器 (精排序)
  文档级 → 段落级 → 千级→百级 → Top-5
```

### 4.6.3 混合搜索

```
用户查询
  ├── 嵌入向量 → Milvus HNSW → Top-30 (向量分数)
  └── BM25 (jieba 分词) → 稀疏搜索 → Top-30
          ↓
    RRF 融合 → Top-20 → 交叉编码器 → Top-5
```

---

# 第五部分: Agent 决策智能

## 5.1 决策溯源

### 5.1.1 设计目标

每个 Agent 决策必须可追溯：为什么选了工具 A？考虑过哪些备选？当时的置信度？

### 5.1.2 决策链数据结构

```
DecisionNode {
  node_id, timestamp,
  prompt_version (commit hash), model_name, temperature,
  decision_type: "routing" | "tool_selection" | "answer_generation",
  candidates: [{option, score, reasoning}],
  selected: str, confidence: float,
  retrieved_docs: [{doc_id, chunk_id, similarity}],
  status: "success" | "error" | "clarification_needed",
  user_confirmed: bool | null
}
```

### 5.1.3 存储

`decision_traces` 表 (MySQL 月分区表)，JSON 存储完整决策链。关联 LangSmith trace_id。

## 5.2 置信度估计

### 5.2.1 四类置信度

| 类型 | 含义 | 来源 | 阈值 |
|------|------|------|------|
| 路由置信度 | 应该路由到此 Agent? | LLM logprobs | <0.7 → 澄清 |
| 检索置信度 | 文档是否相关? | Milvus similarity 分布 | top-1 <0.6 → 低置信度 |
| 事实置信度 | 声明是否被文档支撑? | NLI 模型逐条验证 | <0.5 → 标记 |
| 回答置信度 | 综合判断 | 加权: 事实×0.5 + 检索×0.3 + 路由×0.2 | |

### 5.2.2 低置信度处理

| 区间 | UI | 行为 |
|------|-----|------|
| 0.85-1.00 | 无标记 | 正常 |
| 0.70-0.85 | ⚠️ 仅供参考 | 正常 + 提示 |
| 0.50-0.70 | 🔶 准确性较低 | 提供多选项 |
| <0.50 | 🔴 无法确认 | 拒绝回答, 建议转人工 |

## 5.3 确定性重放

### 5.3.1 三层冻结

```
Layer 1: 状态冻结 → PostgresSaver 加载当时 checkpoint
Layer 2: 配置冻结 → Prompt commit hash + Model + Temperature
Layer 3: 外部依赖 Mock → LLM 录制响应 + 向量检索录制结果
```

### 5.3.2 录制策略

仅当用户反馈 negative 或护栏触发时录制。MinIO 冷存储保留 30 天。

## 5.4 知识生命周期管理

### 5.4.1 七阶段闭环

```
摄入 → 验证 → 冲突检测 → 索引 → 服务 → 反馈 → 废弃
  │                                          │
  └──────────── 知识缺口自动发现 ←───────────┘
```

### 5.4.2 知识冲突管理

新文档入库时:
1. 搜索 cosine > 0.85 的已有分块
2. LLM 逐条比对关键事实
3. 矛盾 → 按权威性/时效性解决

### 5.4.3 知识缺口发现

统计 `lookup_policy` 工具的低分对话 → 聚类未回答问题 → 生成知识缺口工单 → 推送给文档团队。

### 5.4.4 知识文档元数据

每个分块携带: doc_id, source_authority, effective_date, expiry_date, boost_factor, conflicts_with, status。

### 5.4.5 废弃条件

| 条件 | 动作 |
|------|------|
| expiry_date 已过 | Milvus 删除 (MinIO 保留) |
| 被新版本 supersede | 权重→0, 30天后删除 |
| 90 天无命中 | 降级 COLD |
| 人工标记 deprecated | 立即下线 |

## 5.5 Agent 协作模式

### 5.5.1 模式总览

| 模式 | 场景 | 实现 | 触发条件 |
|------|------|------|---------|
| **分类器直路由** (新增) | 单领域明确请求 | 分类器 → 确定性路由 → 子 Agent | 意图置信度 >= 0.85 |
| **Supervisor 委托** (保留) | 单领域模糊请求 | LLM 路由 → 子 Agent | 分类器置信度 < 0.85 |
| **并行 Fan-out** (新增) | 多领域独立请求 | `Send` API 同时启动多子 Agent | 分类器判定 multi_domain |
| **计划-执行** (新增) | 3+ 领域复合任务 | Planner → Executor → Critic | 3+ 领域且有依赖关系 |
| **P2P Handoff** (新增) | 子 Agent 间有依赖 | 条件边: flight_agent → hotel_agent | 子 Agent tool_call 包含目标 Agent |
| **协商模式** (新增) | 预算约束下多目标优化 | 子 Agent 相互调整 → 综合方案 | 用户明确表达约束条件 |

### 5.5.2 并行 Fan-out 详细设计

**适用场景**: 用户同时问 "查航班+酒店+租车"——三个查询互不依赖，可并行。

**实现方式**: LangGraph `Send` API + `Annotated[list, operator.add]` reducer。

**关键设计要点**:
- 并行写入同一 State key 必须用 `operator.add` reducer，防止数据丢失
- 任一子 Agent 失败不影响其他 (独立错误处理)
- Fan-in 节点在所有子 Agent 完成后执行汇总
- 超时保护: 10s 内未完成的子 Agent 跳过

**延迟对比**:

| 执行方式 | 航班 8s + 酒店 6s + 租车 4s | 说明 |
|---------|---------------------------|------|
| 串行 | **18s** | 当前方式 |
| 并行 Fan-out | **8s** | 增强后 (-55%) |

### 5.5.3 P2P Handoff 详细设计

**适用场景**: 航班改签后需要根据新到达时间订酒店——两个子 Agent 有依赖关系。

**实现方式**: 在子 Agent 间增加条件边。

**关键设计要点**:
- 仅允许预定义的 Handoff 路径 (flight→hotel, hotel→car) — 不允许全 Mesh
- Handoff 时携带上下文 (如航班到达时间)
- 不回到 Primary 直接转发，节省 1 次 LLM 调用
- 每个 Handoff 记录到审计日志

### 5.5.4 计划-执行详细设计

**适用场景**: "帮我规划下周三去苏黎世的完整行程"——涉及 3+ 领域且有依赖关系。

**Planner 输出格式**:

```
{
  "plan_id": "plan-abc123",
  "steps": [
    {"id": 1, "domain": "flight", "action": "search", "depends_on": [],
     "params": {"departure": "北京", "arrival": "苏黎世", "date": "2026-04-30"}},
    {"id": 2, "domain": "hotel", "action": "search", "depends_on": [1],
     "params": {"location": "苏黎世", "checkin": "from_step_1.arrival_date"}},
    {"id": 3, "domain": "excursion", "action": "search", "depends_on": [],
     "params": {"location": "苏黎世"}},
    {"id": 4, "domain": "synthesize", "action": "recommend", "depends_on": [1, 2, 3],
     "params": {}}
  ]
}
```

**Executor 按拓扑排序执行**: Wave 1 (Step 1+3 并行) → Wave 2 (Step 2) → Wave 3 (Step 4 汇总)

**成本权衡**: 多一次 Planner LLM 调用 (~3000 Token)，换 40-70% 任务完成率提升。仅对 3+ 领域请求触发。

## 5.6 Agent 自检机制

| 机制 | 触发条件 | 动作 |
|------|---------|------|
| **循环检测** | 连续 3 轮 similarity > 0.90 | 主动声明 "我可能没有完全理解", 建议转人工 |
| **冗余调用** | 同一工具+参数调用 ≥2 次 | 使用缓存结果 |
| **置信度自检** | 任一维度 <0.5 | 拒绝回答, 建议转人工 |
| **心跳** | 每 60s | 检测 LLM/Milvus/DB/Redis 可用性 |

---

# 第六部分: 非功能性架构

## 6.1 SLO 定义

### 6.1.1 服务等级目标

| 服务 | 可用性 | P95 延迟 | 错误率 | 一致性 |
|------|--------|---------|--------|--------|
| **API 网关** | 99.9% | <100ms | <0.1% | — |
| **对话响应 (非流式)** | 99.5% | <8s | <2% | — |
| **对话响应 (流式首 Token)** | 99.5% | <2s | <2% | — |
| **RAG 检索** | 99.9% | <500ms | <1% | Read-after-write |
| **LLM API** | 99.5% | <5s | <3% | — |
| **MySQL** | 99.9% | <50ms | <0.01% | Strong |
| **PostgreSQL (Checkpoint)** | 99.9% | <50ms | <0.01% | Strong |
| **Redis** | 99.9% | <5ms | <0.01% | Eventual |
| **Milvus** | 99.5% | <200ms | <1% | Read-after-write |
| **MinIO** | 99.9% | <100ms | <0.01% | Strong |

### 6.1.2 错误预算

```
99.5% 可用性 = 每月允许 3.6 小时不可用

错误预算分配:
  计划内维护: 2 小时/月
  非计划故障: 1.6 小时/月

预算耗尽 → 冻结发布 → 优先稳定性修复
```

## 6.2 故障模式分析 (FMEA)

### 6.2.1 组件故障影响矩阵

| 组件故障 | 爆炸半径 | 影响 | 降级路径 |
|---------|---------|------|---------|
| **LLM API** | 所有对话 | **严重**: 无 AI 响应 | L2 语义缓存 → 规则引擎 → 转人工 |
| **Milvus** | RAG 检索 | **严重**: 无法查政策 | 告知用户 "政策查询不可用" + 记录知识缺口 |
| **MySQL** | 用户认证/业务数据 | **严重**: 无法登录/查询 | ProxySQL → 从库提升, Orchestrator 自动故障转移 |
| **PostgreSQL** | Agent 记忆 | **严重**: 丧失会话上下文 | Patroni 自动故障转移, 新会话无历史但可对话 |
| **Redis** | 限流/缓存/队列 | **中等**: 缓存降级, 限流失效 | 限流降级为本地内存, 缓存直接穿透到向量库 |
| **MinIO** | 文档存储 | **低**: 新文档无法摄入 | 已索引文档不受影响, 异步队列暂存 |
| **PgBouncer** | 连接池 | **中等**: DB 连接饱和 | PgBouncer HA (第二个实例接管) |

### 6.2.2 降级优先级

```
Level 0: 全功能
Level 1: 无 RAG (仅 LLM + 缓存)
Level 2: 无 LLM (仅缓存 + 规则)
Level 3: 仅人机客服
```

## 6.3 容量规划模型

### 6.3.1 50TB 规模推算

```
假设:
  - 平均文档大小: 100KB (PDF/Office)
  - 总文档数: 50TB / 100KB ≈ 500,000,000 个文档
  - 平均分块: 512 字符/块, 每文档 20 个分块
  - 总分块数: 500M × 20 = 10,000,000,000 (100 亿)
  - 嵌入维度: 768 (text-embedding-3-small)
  - 每向量存储: 768 × 4 bytes = 3KB (float32)
  - 原始向量存储: 100亿 × 3KB ≈ 30TB
  - 加上 HNSW 图开销 (50-100%): 30TB × 1.75 ≈ 52.5TB
  - 总 Milvus 存储需求: ~60TB
```

### 6.3.2 扩展触发点

| 指标 | 当前值 | 触发扩展 | 扩展动作 |
|------|--------|---------|---------|
| Milvus 向量数 | 1 亿 | >80% 分片容量 | 增加 DataNode, 数据重分布 |
| QueryNode 内存 | 80% | 持续 >85% (5min) | 增加 QueryNode |
| MySQL QPS | 500 | >800 (持续) | 增加从库 |
| Redis 内存 | 70% | >85% | 增加节点或启用集群模式 |
| LLM API 速率 | 限流 | 退避次数 >10/min | 增加 API Key 或降级模型 |
| MinIO 存储 | 60% | >80% | 增加节点 |

## 6.4 多租户隔离架构

### 6.4.1 逐层隔离验证

| 层 | 隔离机制 | 验证方式 |
|-----|---------|---------|
| **API** | JWT → user_id 派生 thread_id | `thread_id = "user_{id}:{uuid}"` |
| **State** | Runtime Context (不写入 checkpoint) | `runtime.context.user_id` |
| **数据库** | WHERE passenger_id / user_id 过滤 | SQL 参数化查询 |
| **向量存储** | Milvus Partition Key (按 user 或 org) | `partition_name="user_{id}"` |
| **缓存** | Key 前缀 `"user_{id}:..."` | Redis key namespace |
| **对象存储** | MinIO Bucket Policy 按路径隔离 | `documents/{org_id}/...` |

### 6.4.2 关键原则

- 所有查询必须带租户条件，不可依赖"调用者不会越权"
- 检查点 (Checkpoint) 按 thread_id 隔离，不同用户的 thread_id 天然不同
- 缓存 key 必须包含 user_id 前缀，防止跨用户缓存污染

## 6.5 数据隐私合规

### 6.5.1 PII 检测与脱敏

**输入阶段**: Presidio 实时检测 (姓名/身份证/护照/手机/邮箱) → 自动脱敏或拒绝。

**存储阶段**: 对话记录中的 PII 自动替换为 `[REDACTED]`，原始数据不落盘。

**输出阶段**: 输出护栏检查 PII → 拦截包含敏感信息的 Agent 回复。

### 6.5.2 用户数据权利

| 权利 | 实现 |
|------|------|
| **访问权** | `GET /api/v1/users/{id}/data` 导出所有对话历史、偏好、审计日志 |
| **删除权** | `DELETE /api/v1/users/{id}/data` 删除所有关联数据 (对话/记忆/审计) |
| **可移植权** | JSON 格式导出，支持迁移到其他系统 |
| **限制处理权** | 用户可选择不参与评估数据收集 |

### 6.5.3 数据驻留

- 所有数据存储于 MinIO 国内集群
- LLM API 调用确保数据不出境 (使用国内 API 端点)
- 日志和审计数据不包含原始 PII

## 6.6 用户体验度量

| 指标 | 定义 | 目标 |
|------|------|------|
| **任务完成率** | 用户完成预订/改签/取消 | >85% |
| **首次解决率** | 一次对话解决问题 | >70% |
| **对话效率** | 完成任务所需平均轮数 | <5 轮 |
| **降级率** | 转人工比例 | <10% |
| **满意度** | 赞/(赞+踩) | >80% |
| **弃聊率** | 中途放弃比例 | <15% |

---

# 第七部分: 风险治理与迁移路线图

## 7.1 技术风险登记册

| # | 风险 | 概率 | 影响 | 缓解措施 | 降级方案 |
|---|------|------|------|---------|---------|
| R1 | Milvus 分布式运维复杂度过高 | 中 | 高 | 培训 + 外包运维; 先 POC 验证 | 降级 Qdrant (牺牲扩展性) |
| R2 | 50TB 嵌入成本超预算 | 中 | 高 | 分批处理; IVF_SQ8 量化; 冷数据不嵌入 | 仅对高频文档嵌入 |
| R3 | LLM API 供应商锁定 | 低 | 高 | Provider 抽象层 + 多模型路由 | 切换备选 Provider |
| R4 | PostgreSQL 主库故障导致 Agent 记忆丢失 | 低 | 高 | Patroni HA + 3 副本 + PgBouncer | 新会话无历史但可对话 |
| R5 | 中文文档 OCR 准确率不足 | 中 | 中 | PaddleOCR + MinerU 组合; 人工抽检 | 仅处理原生数字文档 |
| R6 | 提示词版本管理混乱 | 中 | 中 | PromptHub + commit hash 锁定 | 代码内管理 (回退) |
| R7 | 护栏误拦导致用户体验差 | 中 | 中 | 严重度分级; 黄灯放行+记录; A/B 测试 | 降低护栏严格度 |
| R8 | 知识冲突引发错误回答 | 高 | 中 | 冲突检测 + 权威性排序 + 人工审核 | 返回多版本供用户判断 |

## 7.2 现状 vs 目标差距矩阵

| 维度 | 当前状态 | 目标状态 | 差距 | 优先级 |
|------|---------|---------|------|--------|
| **安全** | API Key 硬编码 | Vault 动态密钥 | 大 | P0 |
| **配置** | Dynaconf (失效) | pydantic-settings | 中 | P0 |
| **身份** | passenger_id 硬编码 | JWT → Runtime Context | 大 | P0 |
| **数据库** | SQLite + MySQL 混用 | MySQL + PostgreSQL | 大 | P1 |
| **RAG** | numpy 内存检索 | Qdrant / Milvus | 大 | P1 |
| **记忆** | MemorySaver | PostgresSaver + Store + 摘要 | 大 | P1 |
| **Agent 分层** | 扁平 single-file | 六层架构 | 大 | P1 |
| **文档管线** | 无 | MinIO → 解析 → 分块 → 嵌入 | 新增 | P2 |
| **分布式检索** | 无 | Milvus 分布式 | 新增 | P2 |
| **评估** | 无 | LangSmith + CI 门禁 | 新增 | P2 |
| **护栏** | 无 | 五层纵深防御 | 新增 | P2 |
| **幻觉检测** | 无 | 四层检测栈 | 新增 | P2 |
| **Prompt 管理** | 代码内散落 | PromptHub + 版本化 | 新增 | P2 |
| **成本管理** | 无 | 多模型路由 + Token 预算 | 新增 | P2 |
| **决策溯源** | 无 | DecisionNode + decision_traces | 新增 | P2 |
| **置信度** | 无 | 四类置信度 + 分级处理 | 新增 | P3 |
| **知识生命周期** | 无 | 七阶段闭环 | 新增 | P3 |
| **HA** | 无 | Patroni + ProxySQL + Sentinel | 新增 | P3 |
| **监控** | 无 | Prometheus + Grafana + OTel | 新增 | P3 |

## 7.3 分阶段迁移路线图

### Phase 0: 紧急修复 (1-2 天)

| 步骤 | 内容 |
|------|------|
| P0.1 | 修复 `tools/__init__.py:9,12` f-string bug |
| P0.2 | 修复 `InDBMixin` 导入断裂 |
| P0.3 | 所有 API Key 移至 `.env` |
| P0.4 | 生成新 JWT 密钥 |
| P0.5 | 修改 MySQL 密码 |
| P0.6 | `echo=True` → `echo=settings.DEBUG` |
| P0.7 | 删除 `api/__init__.py` 垃圾代码 |

### Phase 1: 项目结构 + 配置 + 安全 (3-4 天)

| 步骤 | 内容 |
|------|------|
| P1.1 | Poetry (`pyproject.toml`) |
| P1.2 | 新目录结构 (`app/`) |
| P1.3 | `app/core/config.py` (pydantic-settings) |
| P1.4 | `app/core/security.py` (JWT + 密码) |
| P1.5 | `app/core/exceptions.py` |
| P1.6 | `app/core/logging.py` (JSON 结构化) |
| P1.7 | `app/middleware/` (认证 + 限流 + 请求ID) |
| P1.8 | 删除死代码 (3 流程图, finally_graph, Gradio) |

### Phase 2: 数据层升级 (3-4 天)

| 步骤 | 内容 |
|------|------|
| P2.1 | MySQL 创建业务表 (flights, hotels 等) |
| P2.2 | 数据迁移脚本 (SQLite → MySQL) |
| P2.3 | SQLAlchemy async engine + Repository 层 |
| P2.4 | 工具函数从 sqlite3 → MySQL Repository |
| P2.5 | Alembic 迁移 |
| P2.6 | 用户↔乘客映射表 |

### Phase 3: LLM + Agent 系统 + 多 Agent 优化 (4-6 天)

| 步骤 | 内容 | 优先级 |
|------|------|--------|
| P3.1 | LLM Provider 抽象层 | |
| P3.2 | 移除 Qwen-7B, 切换云端 LLM | |
| P3.3 | 参数化子图工厂 (消除重复) | |
| P3.4 | Agent 基类 (重试 + 超时 + 护栏钩子) | |
| P3.5 | Prompt 分离 (代码 → `prompts/`) | |
| P3.6 | 修复提示词拼写错误和时间固化 | |
| P3.7 | `graph_service.py` 编排服务 | |
| **P3.8** | **意图分类器 (Haiku/Flash) 替代 LLM 路由** | **P0** |
| **P3.9** | **并行 Fan-out (Send API) 多领域请求** | **P1** |
| **P3.10** | **Planner Agent + Executor (计划-执行分离)** | **P2** |
| **P3.11** | **P2P Handoff 条件边 (flight→hotel 等)** | **P2** |
| **P3.12** | **Critic Agent 结果验证** | **P2** |
| **P3.13** | **Agent Registry 基础 (为 8+ Agent 预留)** | **P3** |

### Phase 4: RAG + 记忆 + 身份 (4-5 天)

| 步骤 | 内容 |
|------|------|
| P4.1 | Qdrant Docker + 中文分块管线 |
| P4.2 | LangChain Indexing API + SQLRecordManager |
| P4.3 | PostgresSaver + PostgresStore |
| P4.4 | SummarizationNode |
| P4.5 | Runtime Context 身份注入 |
| P4.6 | 工具 ToolRuntime + 所有权验证 |
| P4.7 | 城市映射 MySQL 表 |

### Phase 5: API + 治理基础 (4-5 天)

| 步骤 | 内容 |
|------|------|
| P5.1 | 重写 API 端点 (v1, async, SSE 流式) |
| P5.2 | Refresh Token + 令牌黑名单 |
| P5.3 | 速率限制 (slowapi + Redis) |
| P5.4 | 健康检查端点 |
| P5.5 | LangSmith 集成 (2 环境变量) |
| P5.6 | 基础评估数据集 |
| P5.7 | 输入护栏 Layer 1-2 (Presidio + Llama Guard) |

### Phase 6: 测试 + 部署 (3-4 天)

| 步骤 | 内容 |
|------|------|
| P6.1 | 单元测试 (路由/状态/工具/安全) |
| P6.2 | 集成测试 (API/图流程/RAG) |
| P6.3 | Dockerfile |
| P6.4 | docker-compose.yml (app + mysql + pg + redis + qdrant + nginx) |
| P6.5 | nginx.conf |
| P6.6 | .env.example + README |
| P6.7 | E2E 部署验证 |

### Phase 7: 基础设施 (5-7 天)

| 步骤 | 内容 |
|------|------|
| P7.1 | MinIO 分布式部署 |
| P7.2 | 文档处理管线 (解析器路由 + Celery 队列) |
| P7.3 | Milvus 分布式部署 |
| P7.4 | PostgreSQL HA (Patroni + PgBouncer) |
| P7.5 | MySQL HA (ProxySQL + Orchestrator) |
| P7.6 | Redis Sentinel |
| P7.7 | Prometheus + Grafana 监控 |
| P7.8 | OpenTelemetry 分布式追踪 |

### Phase 8: 治理深度建设 (5-7 天)

| 步骤 | 内容 |
|------|------|
| P8.1 | 五层护栏完整部署 |
| P8.2 | 四层幻觉检测 |
| P8.3 | PromptHub 版本化 |
| P8.4 | 多模型路由 |
| P8.5 | 语义缓存 |
| P8.6 | Token 预算 + 成本归因 |
| P8.7 | CI/CD 评估门禁 |
| P8.8 | 反馈闭环 |

### Phase 9: 决策智能 (5-7 天)

| 步骤 | 内容 |
|------|------|
| P9.1 | 决策溯源 + decision_traces 表 |
| P9.2 | 置信度估计 + 分级处理 |
| P9.3 | 确定性重放 (录制 + 回放) |
| P9.4 | 知识生命周期 (冲突检测 + 缺口发现) |
| P9.5 | Agent 协作模式 (并行/串行/协商) |
| P9.6 | Agent 自检 (循环检测/心跳) |
| P9.7 | 用户体验度量 + 反馈收集 |

### Phase 10: 非功能性完善 (3-5 天)

| 步骤 | 内容 |
|------|------|
| P10.1 | SLO 监控仪表盘 |
| P10.2 | FMEA 故障演练 |
| P10.3 | 容量规划自动化 |
| P10.4 | 多租户隔离验证 |
| P10.5 | PII 脱敏全链路验证 |
| P10.6 | 用户数据删除/导出 API |

**预计总工期**: Phase 0-6 核心交付 18-25 天, Phase 7-10 完整交付 38-51 天

---

# 第八部分: 部署与运维

## 8.1 Docker Compose 拓扑

```yaml
services:
  nginx:       # 反向代理 (80/443)
  app:         # FastAPI (8000)
  mysql:       # MySQL 8.0 (3306) — 业务数据
  postgres:    # PostgreSQL 16 (5432) — Agent 记忆
  redis:       # Redis 7 (6379) — 缓存 + 限流 + 队列
  qdrant:      # Qdrant (6333) — 向量存储 (≤10TB)
  # Phase 7 扩展:
  # milvus-proxy, milvus-querynode × 8, milvus-datanode × 3
  # milvus-indexnode × 2, etcd, pulsar
  # minio × 8 (分布式)
```

## 8.2 高可用拓扑

```
FastAPI (K8s, HPA: 3-20 Pods)
  │
  ├── MySQL: ProxySQL (读写分离) + Orchestrator (故障转移)
  ├── PostgreSQL: PgBouncer (连接池) + HAProxy + Patroni (HA)
  ├── Redis: Sentinel (1主+2从+3哨兵)
  └── Milvus: 3 副本
```

## 8.3 监控告警体系

### 8.3.1 可观测性栈

```
Metrics  → Prometheus → Grafana (仪表盘 + 告警)
Logs     → Loki → Grafana (日志查询)
Traces   → Tempo → Grafana (分布式追踪, OTel)
```

### 8.3.2 核心告警规则

| 告警 | 条件 | 严重度 |
|------|------|--------|
| 后端宕机 | `up{job="fastapi"} == 0` (1min) | Critical |
| 高错误率 | 5xx > 5% (2min) | Critical |
| LLM 错误激增 | `rate(llm_errors[5m]) > 0.1` | Critical |
| P99 延迟 >5s | 2min | Warning |
| Token 成本异常 | 输出 >1M/min | Warning |
| 向量搜索 P95 >1s | 5min | Warning |
| 缓存命中率 <30% | 10min | Warning |

## 8.4 测试体系

```
        ┌─────────┐
        │  E2E    │  关键流程 (10%)
       ┌┴─────────┴┐
       │ Integration│  API + DB + Graph (30%)
      ┌┴────────────┴┐
      │   Unit        │  路由/状态/工具/安全 (60%)
      └───────────────┘
```

**关键测试用例**:
- Unit: Graph 路由 / State reducer / JWT 创建解码 / 工具参数化查询
- Integration: 注册→登录→Token→受保护端点 / 无效 Token→401 / 速率限制
- E2E: 完整对话 (查航班→改签→确认) / 护栏拦截 / 幻觉检测触发

---

# 附录

## 附录 A: 文件映射表

| 当前文件 | 目标位置 | 变更 |
|----------|----------|------|
| `main.py` | `app/main.py` | 应用工厂模式 |
| `config/` | `app/core/config.py` | pydantic-settings |
| `utils/jwt_utils.py` + `password_hash.py` | `app/core/security.py` | 合并 |
| `utils/handler_error.py` | `app/core/exceptions.py` | 结构化异常 |
| `utils/middlewares.py` | `app/middleware/auth.py` | 拆分 |
| `api/routers.py` | `app/api/v1/router.py` | 版本化 |
| `api/graph_api/` | `app/api/v1/graph.py` | 迁移 |
| `api/system_mgt/` | `app/api/v1/auth.py` + `users.py` | 按资源拆分 |
| `graph_chat/state.py` | `app/graph/state.py` | 扩展字段 |
| `graph_chat/graph_gradio.py` | `app/graph/graph.py` | 移除 Gradio |
| `graph_chat/build_child_graph.py` | `app/graph/graph.py` | 参数化工厂 |
| `graph_chat/assistant.py` | `app/graph/agents/primary.py` | Agent 层 |
| `graph_chat/agent_assistant.py` | `app/graph/agents/{flight,hotel,car,excursion}.py` | 拆分 |
| `graph_chat/llm_tavily.py` | `app/infrastructure/llm/` | Provider 抽象 |
| `tools/` | `app/graph/tools/` | 内聚 + MySQL |
| `db/` | `app/db/` | Repository 模式 |

## 附录 B: 依赖变更清单

### 新增

| 包 | 用途 | 阶段 |
|----|------|------|
| `langgraph-checkpoint-postgres` | PostgresSaver | P4 |
| `psycopg[binary,pool]` | PostgreSQL 异步驱动 | P4 |
| `langmem` | SummarizationNode | P4 |
| `langchain-qdrant` | Qdrant 向量存储 | P4 |
| `pymilvus` | Milvus 客户端 | P7 |
| `minio` | MinIO 客户端 | P7 |
| `celery[redis]` | 异步任务 | P7 |
| `slowapi` | 速率限制 | P5 |
| `prometheus-fastapi-instrumentator` | 监控 | P7 |
| `opentelemetry-instrumentation-fastapi` | 追踪 | P7 |
| `nemoguardrails` | 护栏 | P8 |
| `presidio-analyzer` | PII 检测 | P8 |

### 移除

| 包 | 原因 |
|----|------|
| `gradio` | 生产不需要 |
| `langchain-community` (Tavily) | Tavily 移除 |
| `dynaconf` | pydantic-settings 替代 |
| `loguru` | 标准 logging JSON 格式 |
| `sqlite3` (直接使用) | 迁移至 MySQL |

## 附录 C: 技术栈总览

| 层次 | 技术 | 用途 |
|------|------|------|
| **API 框架** | FastAPI | REST + WebSocket |
| **Agent 框架** | LangGraph | StateGraph 多智能体 |
| **LLM** | OpenAI / DeepSeek | 问答 + 工具选择 |
| **向量存储** | Qdrant / Milvus | RAG 检索 |
| **业务数据库** | MySQL 8.0 | 用户/航班/酒店/审计 |
| **Agent 记忆** | PostgreSQL 16 | Checkpoint + Store |
| **缓存** | Redis 7 | 多级缓存 + 限流 + 队列 |
| **对象存储** | MinIO | 50TB 文档 |
| **配置** | pydantic-settings + .env | 类型安全配置 |
| **依赖管理** | Poetry | 锁定 + 虚拟环境 |
| **日志** | Python logging (JSON) | 结构化日志 |
| **监控** | Prometheus + Grafana | 指标 + 告警 |
| **追踪** | OpenTelemetry + Tempo | 分布式追踪 |
| **容器化** | Docker Compose | 部署 |
| **异步任务** | Celery + Redis | 文档处理 |
| **迁移** | Alembic | 数据库版本 |
| **评估** | LangSmith / LangFuse | Agent 评估 |
| **护栏** | NeMo Guardrails | 输入/输出安全 |
| **PII 检测** | Presidio | 敏感信息脱敏 |
| **密钥管理** | HashiCorp Vault | 动态凭证 |
| **API 网关** | APISIX / Nginx | 限流/认证/路由 |
| **HA** | Patroni + ProxySQL + Sentinel | 数据库高可用 |
| **前端** | Vue 3 + TypeScript + Tailwind CSS | 用户端 + 管理端 |
| **状态管理** | Pinia | 认证状态 + 聊天状态 |
| **构建** | Vite | 开发 + 生产构建 |

---

## 第九部分: 前端架构设计

### 9.1 技术栈

| 技术 | 版本 | 用途 |
|------|------|------|
| Vue 3 | ^3.5 | Composition API + `<script setup>` |
| TypeScript | ^5.7 | 类型安全 |
| Vite | ^6.0 | 构建工具 + HMR |
| Tailwind CSS | ^3.4 | 原子化样式 |
| Pinia | ^2.3 | 状态管理 |
| Vue Router | ^4.5 | 客户端路由 |
| marked + DOMPurify | ^15 / ^3.2 | Markdown 渲染 + XSS 防护 |
| Lucide Vue Next | ^0.460 | 图标库 |
| fetch-event-source | ^2.0 | SSE 流式连接 |

### 9.2 路由设计

```
/                  → ChatPage       (需登录)
  /login           → LoginPage      (游客)
  /admin           → AdminPage       (需登录)
    /admin/        → Dashboard      (概览仪表盘)
    /admin/users   → Users          (用户管理)
    /admin/conversations → Conversations (对话监控)
    /admin/documents   → Documents  (文档管理)
```

### 9.3 组件树

```
App.vue
├── LoginPage.vue
│   └── (登录/注册表单, Tab 切换)
│
├── ChatPage.vue
│   ├── SessionSidebar.vue              (左侧会话列表)
│   │   ├── 新建对话按钮
│   │   └── 会话列表 (标题/预览/时间)
│   ├── ChatHeader.vue                  (顶部标题栏)
│   │   ├── 会话选择器
│   │   ├── 分享按钮 → ShareDialog.vue
│   │   └── 新建对话按钮
│   ├── MessageList.vue                 (消息列表, 自动滚动)
│   │   ├── MessageBubble.vue (×N)      (消息气泡)
│   │   │   ├── Markdown 渲染
│   │   │   └── BookingCard.vue         (预订结果卡片)
│   │   └── LoadingDots.vue             (流式加载动画)
│   └── ChatInput.vue                   (输入框)
│       ├── 文本输入 (auto-resize)
│       ├── 文件上传按钮
│       └── 发送按钮
│
└── AdminPage.vue
    ├── 左侧导航 (Dashboard/Users/Conversations/Documents)
    ├── Dashboard.vue → StatsCard.vue (×5)
    ├── Users.vue → DataTable.vue
    ├── Conversations.vue → DataTable.vue
    └── Documents.vue → 上传区 + 文档列表
```

### 9.4 状态管理 (Pinia)

**authStore**:
```
token: string           (localStorage 持久化)
user: User | null       (localStorage 持久化)
isAuthenticated: bool   (computed)
loginAction()           → API login → 写 localStorage
registerAction()        → API register → 写 localStorage
logout()                → 清除 token + user
```

**chatStore**:
```
messages: Message[]         (当前会话消息)
sessions: Session[]         (会话列表)
currentSessionId: string    (当前会话 ID)
isStreaming: bool           (是否正在流式)
sidebarOpen: bool           (侧边栏开关)
addMessage()                (追加消息)
updateLastMessage()         (流式更新最后一条)
newSession()                (新建会话)
selectSession()             (切换会话)
```

### 9.5 数据流

```
SSE 流式对话:
  用户输入 → ChatInput.vue → chatStore.addMessage(user msg)
    → api/chatSSE() → fetch text/event-stream
    → 逐 token 回调 → chatStore.updateLastMessage()
    → 流式结束 → chatStore.setStreaming(false)
    → 解析 BookingCard → MessageBubble 渲染预订卡片

Session 管理:
  新建对话 → chatStore.newSession() → threadId=null
  API 返回 threadId → 存入 sessions[]
  切换会话 → chatStore.selectSession(id) → 加载历史消息
  删除会话 → 从 sessions[] 移除

认证流程:
  LoginPage → authStore.loginAction() → API /auth/login
    → 获取 token → localStorage → router.push('/')
  ChatPage beforeMount: 检查 isAuthenticated → 否则 redirect /login
```

### 9.6 SSE 流式处理

```
fetch() → ReadableStream reader
  → 按 \n 分割数据行
  → 解析 data: {...} JSON
  → {content} → 更新消息气泡 (逐字显示)
  → {thread_id} → 保存会话 ID
  → AbortController 支持取消
```

### 9.7 预订卡片设计

Agent 返回的预订结果渲染为可视化卡片:

**FlightCard**: 蓝色左边框, 飞机图标, 出发→到达 (机场代码), 日期时间, 航班号, 舱位

**HotelCard**: 橙色左边框, 建筑图标, 酒店名称, 位置, 入住/退房日期, 价格层级

**CarRentalCard**: 绿色左边框, 汽车图标, 租车公司, 地点, 起止日期

### 9.8 管理后台

**Dashboard**: 5 个统计卡片 (用户数/对话数/Token/费用/日活)

**Users**: 用户列表表格 (ID/用户名/手机/姓名), 搜索, 分页

**Conversations**: 对话监控列表 (会话ID/用户/消息数/时间/状态)

**Documents**: RAG 文档管理 (上传区/文档列表/状态/操作)

### 9.9 部署

**开发环境**: Vite dev server (:5173) → proxy /api → FastAPI (:8000)

**生产环境**: `vite build` → `dist/` → Nginx 静态文件 + /api 反代

```
Nginx:
  /           → frontend/dist/   (静态文件)
  /api/       → app:8000         (FastAPI 后端)
  /api/graph/chat → SSE 支持    (proxy_buffering off)
```

---

> **文档维护**: 本文件是项目唯一权威架构文档，所有架构决策必须在此文档中体现。代码变更前请先更新此文档。
