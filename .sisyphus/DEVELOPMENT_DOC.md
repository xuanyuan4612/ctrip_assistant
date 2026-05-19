# 携程 AI 助手 — 生产级开发文档

> **版本**: v3.0 (多模态 Agent 架构)  
> **日期**: 2026-05-19  
> **文档范围**: 完整生产级多模态架构 —— 从应用代码到基础设施、从 Agent 治理到决策智能、从非功能需求到迁移路线图、从文本对话到视觉/语音多模态交互  
> **设计原则**: 架构先行 · 分层清晰 · 决策可追溯 · 故障可降级 · 知识可治理 · 模态可插拔  

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

### [第六部分: 多模态能力架构](#第六部分多模态能力架构)
- [6.0 多模态定位与旅行场景](#60-多模态定位与旅行场景)
- [6.1 多模态基础设施 (Layer 1)](#61-多模态基础设施-layer-1)
- [6.2 多模态能力工具 (Layer 2)](#62-多模态能力工具-layer-2)
- [6.3 多模态 Agent 设计 (Layer 3)](#63-多模态-agent-设计-layer-3)
- [6.4 多模态编排 (Layer 4)](#64-多模态编排-layer-4)
- [6.5 多模态 API 层 (Layer 5)](#65-多模态-api-层-layer-5)
- [6.6 多模态治理与安全 (Layer 6)](#66-多模态治理与安全-layer-6)
- [6.7 多模态处理管线](#67-多模态处理管线)
- [6.8 多模态 RAG](#68-多模态-rag)

### [第七部分: 非功能性架构](#第七部分非功能性架构)
- [7.1 SLO 定义](#71-slo-定义)
- [7.2 故障模式分析 (FMEA)](#72-故障模式分析-fmea)
- [7.3 容量规划模型](#73-容量规划模型)
- [7.4 多租户隔离架构](#74-多租户隔离架构)
- [7.5 数据隐私合规](#75-数据隐私合规)
- [7.6 用户体验度量](#76-用户体验度量)
- [7.7 多模态非功能性需求](#77-多模态非功能性需求)

### [第八部分: 风险治理与迁移路线图](#第八部分风险治理与迁移路线图)
- [8.1 技术风险登记册](#81-技术风险登记册)
- [8.2 现状 vs 目标差距矩阵](#82-现状-vs-目标差距矩阵)
- [8.3 分阶段迁移路线图](#83-分阶段迁移路线图)

### [第九部分: 部署与运维](#第九部分部署与运维)
- [9.1 Docker Compose 拓扑](#91-docker-compose-拓扑)
- [9.2 高可用拓扑](#92-高可用拓扑)
- [9.3 监控告警体系](#93-监控告警体系)
- [9.4 测试体系](#94-测试体系)

### [第十部分: 前端多模态架构](#第十部分前端多模态架构)
- [10.1 多模态 UI 组件](#101-多模态-ui-组件)
- [10.2 图片上传与预览](#102-图片上传与预览)
- [10.3 语音输入与输出](#103-语音输入与输出)

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
| **形态** | 多模态多智能体对话系统 (LangGraph Supervisor 模式) |
| **模态** | 文本 (主要) + 图片 (登机牌/证件/行程单截图) + 语音 (免手操作) |
| **入口** | FastAPI REST API + WebSocket (语音), Multipart 上传 (图片) |
| **LLM** | 云端 LLM (OpenAI / DeepSeek) + 视觉 LLM (GPT-4o / Qwen-VL)，Provider 抽象层可切换 |
| **数据库** | MySQL (业务数据) + PostgreSQL (Agent 记忆) |
| **用户规模** | 数千认证用户 |
| **文档规模** | 50TB 混合文档 (PDF / Office / 结构化数据 / 图片 / 实时流) |
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
| ADR-14 | **多模态作为可插拔能力 (P1)** | 当前系统纯文本，多模态通过 Provider 抽象层 + Modality Detector 节点按需激活，不支持模态时自动降级为文本；旅行场景核心模态: 图片 (登机牌/证件/行程单截图)、语音 (免手操作)、视频 (暂不启用) |
| ADR-15 | **视觉模型: GPT-4V → Qwen-VL 演进 (P1)** | 初期使用 GPT-4o (已有备份模型，支持视觉)；中期迁移至 Qwen-VL-Max (国内部署、成本更低、中文 OCR 更优)；视觉模型仅在检测到图片输入时触发 |
| ADR-16 | **语音管线: 客户端预处理优先 (P1)** | 语音在客户端完成 VAD (语音活动检测) → 服务端仅接收 Whisper 转写后的文本，同时保留原始音频用于合规审计；TTS 在客户端执行 (Web Speech API / Edge TTS)，减少服务端 GPU 压力 |
| ADR-17 | **多模态内容安全分层 (P1)** | 输入层: NSFW 检测 + PII 脱敏 (Presidio 扩展至图片) → 护栏层: Llama Guard 多模态版本 → 输出层: 视觉幻觉检测；图片上传即检测，不安全内容拒绝处理 |
| ADR-18 | **CLIP 多模态嵌入 (P2)** | 50TB 文档中包含大量图片 (PDF 截图、行程单照片等)，启用 CLIP 多模态嵌入实现文搜图 + 图搜图，与文本嵌入并存于 Milvus 不同 Collection

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

### 3.1.7 多模态 LLM Provider 扩展

**设计目标**: 在现有 `AbstractLLMProvider` 接口上扩展多模态能力，支持视觉理解模型。

**接口扩展**:
```
AbstractLLMProvider (扩展):
  ├── get_chat_model() → BaseChatModel         # 文本模型 (不变)
  ├── get_vision_model() → BaseChatModel       # 视觉模型 (新增)
  │    配置: vision_model, max_image_size, supported_formats
  ├── get_embedding_model() → Embeddings       # 文本嵌入 (不变)
  ├── get_multimodal_embedding() → Embeddings  # 多模态嵌入 (新增, CLIP)
  └── health_check() → bool

OpenAIProvider:
  ├── get_chat_model() → ChatOpenAI(model="deepseek-chat")
  ├── get_vision_model() → ChatOpenAI(model="gpt-4o")  # GPT-4o 支持视觉
  └── get_multimodal_embedding() → OpenAIEmbeddings(model="clip-vit-large-patch14")

QwenVLProvider (新增):
  ├── get_chat_model() → ChatOpenAI(model="qwen-vl-max", base_url="...")
  ├── get_vision_model() → 同上 (Qwen-VL 统一文本+视觉)
  └── get_multimodal_embedding() → 本地 CLIP 模型或 API
```

### 3.1.8 语音管线基础设施

```
客户端 (浏览器/小程序):
  ├── MediaRecorder API → VAD (语音活动检测) → Opus 编码
  └── WebSocket → 发送音频流

服务端:
  ├── Whisper API (OpenAI) 或 faster-whisper (本地 GPU)
  │   模型: whisper-1 (API) / large-v3 (本地)
  │   延迟目标: <2s 首 Token
  └── 输出: {text: str, language: str, segments: [{start, end, text}]}

TTS (客户端优先, 减少服务端负载):
  ├── 浏览器: Web Speech API (免费, 零延迟)
  ├── Edge TTS: 微软语音合成 (中文自然度高)
  └── 服务端备用: OpenAI TTS (tts-1-hd, 仅在客户端不支持时)
```

### 3.1.9 多模态对象存储 (MinIO)

在现有 MinIO 存储分层基础上扩展多模态 Bucket:

```
MinIO 多模态 Bucket:
  ├── images/raw/         # 用户上传原始图片 (30 天后转 WARM)
  ├── images/processed/   # 压缩/脱敏后的图片 (对话期间 HOT, 30 天后删除)
  ├── images/thumbnails/  # 缩略图 (HOT, 用于对话列表预览)
  ├── audio/              # 语音输入原始音频 (7 天后删除, 审计除外)
  └── multimodal-vectors/ # CLIP 向量快照 (365 天过期)

图片处理管线 (上传时):
  1. 格式验证 (JPEG/PNG/WebP, 最大 20MB)
  2. 压缩 (max 2048px 长边, WebP 格式, 质量 85%)
  3. NSFW 检测 (nudenet / safety-checker)
  4. PII 检测 (Presidio OCR → 护照/身份证号脱敏)
  5. 生成缩略图 (256px, 用于对话列表)
  6. 存入 processed/ bucket, 原始图存入 raw/
```

### 3.1.10 多模态嵌入服务

```
CLIP 嵌入服务 (独立 GPU Pod 或 API):
  模型: ViT-L/14 (OpenAI CLIP) 或 Chinese-CLIP (中文优化)
  维度: 768 (与 text-embedding-3-small 对齐)
  用途:
    ├── 图片语义搜索 (文搜图: "登机牌截图" → 相关图片)
    ├── 图片去重 (cosine > 0.99 的图片视为重复)
    └── 图文联合检索 (Milvus 多 Collection 融合)

Milvus 多模态 Collection:
  ├── text_vectors (Collection): 文本嵌入 (现有, 1-2 亿向量)
  ├── image_vectors (Collection): 图片 CLIP 嵌入 (新增, 预计 100M 向量)
  └── 检索融合: text_results + image_results → RRF → Top-K
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
| `analyze_image` | 读 | 需 user_id (审计) | 视觉 LLM 理解 |
| `extract_document_text` | 读 | 无 | OCR 提取 |
| `parse_boarding_pass` | 读 | 需 passenger_id | 结构化提取登机牌 |
| `transcribe_audio` | 读 | 需 user_id (审计) | ASR 语音转文字 |
| `search_multimodal` | 读 | 无 | 多模态 RAG 检索 |

### 3.2.5 多模态工具定义

**图片分析工具**:
```python
@tool
def analyze_image(
    image_data: str,  # base64 编码的图片
    query: str,       # 用户关于图片的问题
    runtime: ToolRuntime[UserContext, State],
) -> ToolResult:
    """
    使用视觉 LLM 分析用户上传的图片。
    支持: 登机牌、证件照片、行程单截图、错误页面截图、旅游景点照片。

    安全要求:
      - 上传时已通过 NSFW 检测和 PII 脱敏
      - 记录审计日志
    """
    # 获取视觉模型
    vision_llm = runtime.context.llm_provider.get_vision_model()

    # 构造多模态消息
    message = HumanMessage(content=[
        {"type": "text", "text": query},
        {"type": "image_url", "image_url": {"url": f"data:image/webp;base64,{image_data}"}},
    ])

    result = vision_llm.invoke([message])
    return ToolResult(status="success", data={"analysis": result.content})
```

**OCR 文档提取工具**:
```python
@tool
def extract_document_text(
    image_data: str,
    doc_type: Literal["boarding_pass", "id_card", "itinerary", "generic"] = "generic",
    runtime: ToolRuntime[UserContext, State],
) -> ToolResult:
    """
    从图片中提取结构化文本。
    登机牌: 航班号, 日期, 座位号, 登机口
    身份证: 姓名, 证件号 (脱敏后返回)
    行程单: 出发/到达, 日期, 航班号
    """
    # 根据 doc_type 选择 OCR 策略
    if doc_type == "boarding_pass":
        # 使用视觉 LLM + structured output 提取登机牌字段
        ...
    elif doc_type == "id_card":
        # 使用 PaddleOCR + Presidio PII 脱敏
        ...
```

**语音转写工具**:
```python
@tool
def transcribe_audio(
    audio_data: str,  # base64 编码的音频 (Opus/WebM)
    language: str = "zh",
    runtime: ToolRuntime[UserContext, State],
) -> ToolResult:
    """
    将语音输入转写为文本。
    客户端已完成 VAD, 服务端仅接收有效语音片段。
    """
    from app.infrastructure.audio import get_asr_provider
    asr = get_asr_provider()
    text = asr.transcribe(audio_data, language=language)
    return ToolResult(status="success", data={"text": text, "language": language})
```

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

### 3.3.5a 模态检测节点 (Modality Detector)

**设计目标**: 在意图分类之前检测用户输入中是否包含非文本内容，决定是否激活多模态处理管线。

```
输入消息 → Modality Detector (规则引擎, <1ms)
  │
  ├── has_images? → 激活 Vision Pipeline
  │   ├── 图片预处理 (压缩/安全检查) → Vision LLM 理解
  │   └── 提取结构化信息注入 State
  │
  ├── has_audio? → 激活 Audio Pipeline
  │   └── ASR 转写 → 文本注入 State
  │
  ├── has_document? → 激活 Document Pipeline
  │   └── OCR 提取 → 结构化数据注入 State
  │
  └── text_only → 跳过, 直接进入意图分类

检测规则:
  - 图片: HumanMessage.content 中包含 {"type": "image_url", ...}
  - 音频: 消息附带 audio_data 字段
  - 文档: 用户表述含 "登机牌"/"行程单"/"证件" 且有图片
```

### 3.3.5b 多模态 Agent 设计

**多模态 Agent 基类扩展**:
```python
class MultimodalAgent(BaseAgent):
    """支持多模态输入的 Agent。扩展自 BaseAgent，增加视觉理解能力。"""

    def __init__(self, runnable, vision_runnable=None, ...):
        super().__init__(runnable, ...)
        self.vision_runnable = vision_runnable  # 视觉 LLM runnable

    def preprocess_multimodal(self, state: State) -> State:
        """预处理多模态输入: 图片转结构化文本"""
        last_msg = state["messages"][-1]
        if has_image_content(last_msg):
            # 1. 图片安全检查 (NSFW + PII)
            # 2. 视觉 LLM 理解 → 文本描述
            # 3. OCR 提取结构化字段
            # 4. 注入到 State 中
            vision_result = self.vision_runnable.invoke(last_msg)
            state = inject_vision_context(state, vision_result)
        return state

    def invoke(self, state, config):
        state = self.preprocess_multimodal(state)
        return super().invoke(state, config)
```

### 3.3.5c 视觉 Agent 路由策略

根据图片内容决定路由目标:

| 图片类型 | 检测信号 | 路由目标 | 处理方式 |
|---------|---------|---------|---------|
| **登机牌照片** | OCR 检测到 "BOARDING PASS" / 航班号 + 日期 + 座位号 | `flight_agent` | 提取信息 → 自动填充改签/查询参数 |
| **证件照片** | PII 检测到护照/身份证号码 | `primary_assistant` | 脱敏处理 → 身份验证 → 查询关联订单 |
| **行程单截图** | 检测到出发/到达 + 日期 + 航班号组合 | `flight_agent` | 结构化提取 → 关联查询航班状态 |
| **酒店预订截图** | 检测到酒店名 + 入住/退房日期 | `hotel_agent` | 提取信息 → 查询/修改预订 |
| **错误页面截图** | 文本含 "error"/"失败"/"不可用" | `primary_assistant` | 故障诊断 → 降级建议 → 记录 Bug |
| **旅游景点照片** | 自然场景 + 无文本 | `excursion_agent` | 地标识别 → 推荐相关行程 |
| **通用图片** | 不匹配上述任何规则 | `primary_assistant` | 通用视觉理解 → 回答用户问题 |

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
modality_detector (规则引擎, <1ms)
  │
  ├── has_images → image_preprocessor (压缩 + NSFW + PII 脱敏)
  │       │
  │       ▼
  │   vision_analyzer (Vision LLM → 图片内容理解 + OCR 提取)
  │       │
  │       └──→ intent_classifier (继续)
  │
  ├── has_audio → audio_transcriber (ASR → 文本)
  │       │
  │       └──→ intent_classifier (继续)
  │
  └── text_only → intent_classifier
        │
        ▼
  intent_classifier (Haiku, 40ms)
    │
    ├── single_domain (75%) ──→ 确定性路由 ──→ 对应子 Agent
    │   (含 vision_single: 登机牌 → flight_agent 等)
    │
    ├── multi_domain (15%) ──→ Fan-out (Send API)
    │
    ├── complex (5%, 3+ domains) ──→ planner_agent ──→ executor
    │
    └── low_confidence ──→ fallback_llm_router
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
  POST   /api/v1/graph/chat          # 文本对话 (JSON)
  POST   /api/v1/graph/chat/multimodal  # 多模态对话 (multipart/form-data: text + images[])
  WS     /api/v1/graph/chat/voice    # 语音对话 (WebSocket + 流式音频)
  GET    /api/v1/graph/sessions      # 用户会话列表
  GET    /api/v1/graph/sessions/{id} # 会话详情
  DELETE /api/v1/graph/sessions/{id} # 删除会话 (级联删除关联图片/音频)

系统:
  GET    /api/v1/health              # 健康检查
  GET    /api/v1/metrics             # Prometheus 指标
```

### 3.5.3 流式输出 (SSE)

```
POST /api/v1/graph/chat
  → SSE events:
    event: thinking     → {agent, status}
    event: modality     → {type: "image_analysis" | "ocr" | "audio_transcription", ...}  # 多模态
    event: tool_call    → {tool, args}
    event: interrupt    → {message, requires_confirmation}
    event: token        → {content}
    event: done         → {session_id, cost, modalities_used: ["text", "image"]}
```

### 3.5.3a 多模态请求格式

**JSON (base64 编码图片)**:
```json
{
  "user_input": "帮我看下这张登机牌，我的航班是哪个登机口？",
  "images": [
    {
      "data": "iVBORw0KGgoAAAANSUhEUgAA...",  // base64 编码的 WebP 图片
      "mime_type": "image/webp",
      "label": "登机牌照片"
    }
  ],
  "stream": true
}
```

**Multipart Form (二进制图片)**:
```
POST /api/v1/graph/chat/multimodal
Content-Type: multipart/form-data

--boundary
Content-Disposition: form-data; name="user_input"
查下这个航班有没有延误

--boundary
Content-Disposition: form-data; name="images"; filename="boarding_pass.jpg"
Content-Type: image/jpeg
(binary data)

--boundary
Content-Disposition: form-data; name="stream"
true
```

**WebSocket (实时语音)**:
```
ws://host:8000/api/v1/graph/chat/voice
→ 客户端发送: 二进制音频帧 (Opus 编码, 20ms 帧)
→ 服务端返回: JSON 文本消息 {type: "transcription_interim", text: "帮我查..."}
→ 服务端返回: JSON 文本消息 {type: "transcription_final", text: "帮我查下周三的航班"}
→ 服务端返回: SSE 事件 (与文本对话相同)
→ 服务端返回: JSON 音频帧 {type: "tts_audio", format: "opus", data: "base64..."}  # 可选 TTS
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
  工具: regex + Presidio (文本) + NSFW 检测器 (图片) + 音频 VAD
  覆盖: PII 检测、敏感词过滤、格式校验、图片 NSFW、音频静音检测

Layer 2: 小模型分类 (百毫秒级)
  工具: Llama Guard (文本+图片多模态版本) / NeMo self_check
  覆盖: 内容安全、越狱检测、主题控制、图片敏感内容、音频违规内容

Layer 3: Agent 执行护栏 (内嵌)
  工具: NeMo GuardrailsMiddleware (每个节点)
  覆盖: 工具调用权限、参数校验、多模态内容访问控制

Layer 4: 输出验证 (秒级)
  工具: 幻觉检测 + 事实性校验 + 视觉幻觉检测 (新增)
  覆盖: 生成内容 vs 检索文档一致性、图片分析结果 vs OCR 文本一致性

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

**视觉幻觉检测 (新增)**:
```
Layer V1: 视觉事实性
  - 图片分析输出 vs OCR 提取的文本 → 交叉验证
  - 例: Vision LLM 说 "登机口 A12", OCR 提取 "Gate B5" → 矛盾 → 阻断

Layer V2: 视觉引用验证
  - 分析结果中的每个字段是否可追溯到图片中的视觉元素
  - 标注: "该信息来自图片的哪个区域"

Layer V3: 多模态交叉验证
  - 同一图片的不同 Vision 模型分析结果对比
  - 分歧较大的字段 → 标注为低置信度
```

**设计要点**:
- NLI 模型用于生产 (快速/准确/廉价)，LLM-as-Judge 用于高精度场景
- 不确定时不回答 (Abstention) 优于给出错误答案
- 视觉幻觉 = 最常见的多模态失败模式，必须优先检测

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

# 第六部分: 多模态能力架构

## 6.0 多模态定位与旅行场景

### 6.0.1 为什么旅行助手需要多模态

| 用户场景 | 纯文本痛点 | 多模态方案 |
|---------|-----------|-----------|
| **查登机牌信息** | 用户需手动输入航班号、日期、登机口 (6 个字段，易出错) | 拍照上传 → OCR 自动提取 → 一键查询 |
| **确认证件信息** | 需手动输入护照号/身份证号 (PII 安全风险) | 拍照 → 脱敏提取 → 仅匹配数据库 (不存储明文) |
| **行程单识别** | 旅行社发的行程单截图，需逐条手动录入 | 截图 → 结构化提取 → 自动填充航班+酒店查询 |
| **故障报修** | 描述半天说不清楚错误页面 | 截图 → Vision LLM 理解错误 → 自动诊断 + 建议 |
| **免手操作** | 开车/拎行李时无法打字 | 语音输入 → ASR 转写 → 正常对话流程 |
| **地标识别** | "那个山上的白塔是什么景点" 难以文字描述 | 拍照 → 视觉识别 → 推荐行程 |

### 6.0.2 模态支持优先级

| 优先级 | 模态 | 延迟要求 | 成本影响 | 启用条件 |
|--------|------|---------|---------|---------|
| **P0** | 文本 (Text) | <8s | 低 | 始终启用 (当前) |
| **P1** | 图片 (Image) | <5s (含 Vision LLM) | 中 (GPT-4o: $0.0025/图) | 用户上传图片时自动激活 |
| **P1** | 语音输入 (Voice→Text) | <2s (ASR) | 低 (Whisper: $0.006/min) | 客户端请求语音模式时启用 |
| **P2** | 语音输出 (Text→Voice) | <1s (TTS 首块) | 极低 (客户端免费 TTS) | 客户端支持时自动启用 |
| **P3** | 视频 (Video) | — | 高 | 暂不启用 (旅行场景无强需求) |

### 6.0.3 模态可插拔设计原则

所有模态遵循 **能力声明 → 按需激活 → 不可用时优雅降级** 原则:

```
系统启动 → 检测可用模态:
  ├── Vision LLM 可用? → 注册 image 模态
  ├── ASR 服务可用?   → 注册 voice 模态
  └── TTS 可用?       → 注册 audio_output 模态

请求到达 → 检测请求模态:
  ├── 请求含图片 且 image 模态已注册 → 激活 Vision Pipeline
  ├── 请求含图片 但 image 模态不可用 → 告知 "图片功能暂时不可用, 请用文字描述"
  └── 纯文本请求 → 正常处理 (无影响)
```

---

## 6.1 多模态基础设施 (Layer 1)

### 6.1.1 多模态 Provider 注册

```
app/infrastructure/
  ├── llm/
  │   ├── base.py           # AbstractLLMProvider (扩展 get_vision_model)
  │   ├── openai.py         # OpenAIProvider (get_vision_model → gpt-4o)
  │   ├── deepseek.py       # DeepSeekProvider
  │   └── qwen_vl.py        # QwenVLProvider (新增, 本地/云端)
  ├── audio/
  │   ├── base.py           # AbstractASRProvider (transcribe)
  │   ├── whisper_api.py    # OpenAI Whisper API
  │   └── whisper_local.py  # faster-whisper 本地部署
  ├── vision/
  │   ├── preprocessor.py   # 图片预处理 (压缩/格式化/NSFW/PII)
  │   └── safety.py         # NSFW 检测 + PII 脱敏
  ├── vector/
  │   ├── milvus.py         # 文本嵌入 (不变)
  │   └── clip.py           # CLIP 多模态嵌入 (新增)
  └── storage/
      └── minio.py          # 扩展多模态 Bucket
```

### 6.1.2 多模态配置

```python
# app/core/config.py 新增字段
class Settings(BaseSettings):
    # === 多模态配置 ===

    # 视觉模型
    VISION_MODEL: str = "gpt-4o"         # 默认视觉模型
    VISION_MODEL_BACKUP: str = "qwen-vl-max"  # 降级视觉模型
    VISION_MODEL_MAX_TOKENS: int = 1024  # 视觉分析最大输出

    # 图片处理
    MAX_IMAGE_SIZE_MB: int = 20          # 单张图片大小上限
    MAX_IMAGES_PER_REQUEST: int = 5      # 单次请求图片数上限
    IMAGE_MAX_DIMENSION: int = 2048      # 图片最长边 (px)
    IMAGE_FORMAT: str = "webp"           # 统一压缩格式
    IMAGE_QUALITY: int = 85              # 压缩质量

    # 语音
    ASR_PROVIDER: str = "whisper_api"    # whisper_api | whisper_local
    ASR_MODEL: str = "whisper-1"         # ASR 模型
    ASR_LANGUAGE: str = "zh"             # 默认语言
    TTS_PROVIDER: str = "client"         # client (浏览器) | edge | openai
    TTS_VOICE: str = "zh-CN-XiaoxiaoNeural"  # 默认语音

    # 多模态嵌入
    CLIP_MODEL: str = "ViT-L/14"         # CLIP 模型
    CLIP_EMBEDDING_DIM: int = 768        # 嵌入维度

    # 图片安全
    IMAGE_SAFETY_ENABLED: bool = True    # 是否启用图片安全检查
    IMAGE_NSFW_THRESHOLD: float = 0.7    # NSFW 检测阈值
```

---

## 6.2 多模态能力工具 (Layer 2)

### 6.2.1 完整多模态工具目录

```
app/graph/tools/
  ├── business/             # 业务工具 (不变)
  ├── knowledge/            # 知识检索工具
  │   └── multimodal_search.py  # 多模态 RAG 检索 (新增)
  ├── vision/               # 视觉工具 (新增)
  │   ├── analyze_image.py  # 通用图片理解 (Vision LLM)
  │   ├── extract_document.py  # OCR 文档提取
  │   ├── parse_boarding_pass.py  # 登机牌结构化解析
  │   ├── recognize_landmark.py   # 地标识别
  │   └── compare_screenshots.py  # 前后截图对比 (故障诊断)
  ├── audio/                # 音频工具 (新增)
  │   ├── transcribe.py     # 语音转文字 (ASR)
  │   └── synthesize.py     # 文字转语音 (TTS, 服务端备用)
  └── system/               # 系统工具 (不变)
```

### 6.2.2 登机牌解析工具 (核心多模态应用)

```python
@tool
def parse_boarding_pass(
    image_data: str,
    runtime: ToolRuntime[UserContext, State],
) -> ToolResult:
    """
    从登机牌图片中提取结构化航班信息。
    这是最重要的多模态工具 — 旅行场景中 60% 的图片交互都是登机牌查询。

    提取字段: 乘客姓名, 航班号, 出发/到达机场, 日期, 登机时间, 登机口, 座位号
    """
    # 1. 图片预处理
    preprocessed = preprocess_image(image_data)

    # 2. 视觉 LLM 理解 + structured output
    vision_llm = runtime.context.llm_provider.get_vision_model()
    prompt = """
    从登机牌图片中提取以下字段。如果某个字段不可见，返回 null。
    - passenger_name: 乘客姓名
    - flight_number: 航班号 (如 CA1234)
    - departure_airport: 出发机场代码 (如 PEK)
    - arrival_airport: 到达机场代码 (如 ZRH)
    - departure_date: 出发日期 (YYYY-MM-DD)
    - boarding_time: 登机时间 (HH:MM)
    - gate: 登机口
    - seat: 座位号
    """
    result = vision_llm.invoke_with_image(preprocessed, prompt)

    # 3. 交叉验证: OCR 文本 vs Vision 理解
    ocr_text = ocr_extract(preprocessed)
    cross_validate(result, ocr_text)  # 不一致 → 标记低置信度

    # 4. 审计
    _audit("parse_boarding_pass", runtime.context.user_id,
           {"flight_number": result.flight_number})

    return ToolResult(status="success", data=result.model_dump())
```

---

## 6.3 多模态 Agent 设计 (Layer 3)

### 6.3.1 多模态 Prompt 模板

**Primary Agent 多模态 System Prompt 扩展**:
```python
PRIMARY_SYSTEM_PROMPT = """
您是携程瑞士航空公司的多模态客户服务助理。

【文本能力】
- 搜索航班、酒店、租车、旅行信息
- 帮助用户预订/改签/取消订单
- 查询公司政策和常见问题

【图片能力】
- 识别登机牌照片 → 自动提取航班信息, 一键查询航班状态/改签
- 识别证件照片 → 验证身份关联订单 (证件号会脱敏处理, 系统不存储)
- 识别行程单截图 → 结构化提取行程, 自动填充查询参数
- 识别错误页面截图 → 诊断问题, 提供解决方案
- 识别旅游景点照片 → 推荐相关游玩项目

【语音能力】  (如果用户启用了语音模式)
- 接收语音输入, 自动转写为文字
- 可用语音回复 (需要用户设备支持)

【安全声明】
- 所有上传的图片在分析后 30 天自动删除
- 证件类图片中的敏感信息 (证件号、姓名) 会脱敏处理
- 对话结束后可随时删除您上传的所有图片

【当前用户信息】
{user_info}

当前时间: {time}
"""
```

### 6.3.2 视觉 Agent 路由增强

```python
# app/graph/agents/classifier.py 扩展
class IntentClassifier:
    """意图分类器, 新增图片意图检测"""

    IMAGE_INTENT_MAP = {
        "boarding_pass": "flight",       # 登机牌 → 航班 Agent
        "id_document": "primary",         # 证件 → 主 Agent (身份验证)
        "itinerary": "flight",            # 行程单 → 航班 Agent
        "hotel_booking": "hotel",         # 酒店预订截图 → 酒店 Agent
        "error_screenshot": "primary",    # 错误截图 → 主 Agent (诊断)
        "landmark": "excursion",          # 地标 → 旅行 Agent
        "generic_image": "primary",       # 通用图片 → 主 Agent
    }

    def classify(self, state: State) -> dict:
        # 1. 检测是否有图片
        if has_images := self._detect_images(state):
            # 2. 快速图片分类 (OCR + 轻量视觉特征)
            image_type = self._classify_image_type(state["images"][0])
            # 3. 路由到对应 Agent
            intent = self.IMAGE_INTENT_MAP.get(image_type, "primary")
            return {"intent": intent, "confidence": 0.90, "modality": "image"}

        # 4. 文本意图分类 (不变)
        return self._classify_text(state)
```

---

## 6.4 多模态编排 (Layer 4)

### 6.4.1 多模态 State 扩展

```python
class State(TypedDict):
    # 原有字段 (不变)
    messages: Annotated[list[AnyMessage], add_messages]
    user_id: int
    passenger_id: str
    # ...

    # 多模态扩展 (新增)
    images: Annotated[list[ImageAttachment], operator.add]  # 当前轮次的图片
    image_analysis: dict  # Vision LLM 分析结果
    ocr_text: str         # OCR 提取的文本
    modality_used: list[str]  # ["text", "image", "voice"]

    # 图片元数据
    image_attachments: Annotated[list[ImageMeta], operator.add]
    # ImageMeta: {image_id, mime_type, size, safety_check_passed, pii_redacted}

class ImageAttachment(TypedDict):
    image_id: str         # UUID
    data: str             # base64 编码的图片
    mime_type: str        # image/webp
    label: str | None     # 用户标注 (如 "登机牌")
    preprocessed: bool    # 是否已预处理
```

### 6.4.2 多模态图节点定义

```
modality_detector (规则引擎, <1ms):
  输入: State.messages[-1]
  检测: HumanMessage.content 中是否有 image_url / audio 内容
  输出: {modality: "text" | "image" | "voice" | "mixed"}

image_preprocessor (<500ms):
  输入: raw images
  处理: 格式验证 → 压缩 → NSFW检测 → PII脱敏 → 生成缩略图
  输出: ImageMeta[] + preprocessed_images

vision_analyzer (<3s):
  输入: preprocessed images + user query
  处理: Vision LLM 理解 + OCR 提取
  输出: image_analysis dict + ocr_text

audio_transcriber (<2s):
  输入: audio data
  处理: ASR 转写
  输出: transcribed text → 注入 State.messages

intent_classifier (40ms):
  增强: 图片意图分类 (登机牌→flight, 证件→primary, ...)
```

### 6.4.3 多模态混合对话流

```
用户: [上传登机牌照片] + "这班航班能改签到明天吗?"

  modality_detector → "mixed" (image + text)
    │
    ├── image_preprocessor → NSFW通过, PII脱敏
    ├── vision_analyzer → {flight_number: "CA1234", date: "2026-05-20", ...}
    └── audio_transcriber → (skip, no audio)
    │
    ▼
  intent_classifier:
    图片检测: "boarding_pass" → intent="flight", confidence=0.92
    文本检测: "改签航班" → intent="flight", confidence=0.88
    综合: intent="flight" (image + text 一致)
    │
    ▼
  flight_agent:
    上下文: flight_number=CA1234, date=2026-05-20 (来自图片)
    意图: 改签到明天 (2026-05-21)
    操作: search_flights(CA1234, 2026-05-21) → 展示可选航班
```

---

## 6.5 多模态 API 层 (Layer 5)

### 6.5.1 多模态聊天端点

```python
# app/api/v1/graph.py

@router.post("/chat/multimodal")
async def graph_chat_multimodal(
    user_input: str = Form(...),
    images: list[UploadFile] = File(default=[]),
    stream: bool = Form(default=False),
    request: Request = None,
    current_user: User = Depends(get_current_user),
):
    """
    多模态对话 — 支持文本 + 图片 (multipart/form-data)。

    限制:
      - 最多 5 张图片
      - 单张最大 20MB
      - 仅支持 JPEG/PNG/WebP 格式
    """
    # 1. 验证图片
    if len(images) > settings.MAX_IMAGES_PER_REQUEST:
        raise ValidationError(f"最多上传 {settings.MAX_IMAGES_PER_REQUEST} 张图片")

    # 2. 预处理图片 (压缩 + 安全检查)
    processed_images = []
    for img in images:
        data = await img.read()
        # 大小检查
        if len(data) > settings.MAX_IMAGE_SIZE_MB * 1024 * 1024:
            raise ValidationError(f"图片 {img.filename} 超过 {settings.MAX_IMAGE_SIZE_MB}MB 限制")
        # 格式验证 + 压缩 + 安全检查
        processed = await preprocess_image(data)
        if not processed.safety_check_passed:
            raise ValidationError("图片包含违规内容, 无法处理")
        processed_images.append(processed)

    # 3. 构建多模态消息
    message_content = [{"type": "text", "text": user_input}]
    for img in processed_images:
        message_content.append({
            "type": "image_url",
            "image_url": {"url": f"data:{img.mime_type};base64,{img.base64_data}"}
        })

    # 4. 调用编排层
    graph = get_graph()
    human_msg = HumanMessage(content=message_content)
    # ... (流式/非流式处理逻辑同 /chat)
```

---

## 6.6 多模态治理与安全 (Layer 6)

### 6.6.1 图片输入安全检测流程

```
用户上传图片
  │
  ▼
[格式验证] (ms 级)
  - 魔数检测 (JPEG: FF D8, PNG: 89 50 4E 47, WebP: 52 49 46 46)
  - 扩展名 vs 实际格式一致?
  - 大小 ≤ 20MB, 尺寸 ≤ 4096×4096
  │ 失败 → 拒绝 (400)
  ▼
[NSFW 检测] (200ms)
  - 模型: nudenet / OpenNSFW / safety-checker
  - 阈值: >0.7 → 拒绝 (422 "图片包含不当内容")
  │ 失败 → 拒绝
  ▼
[PII 检测] (500ms)
  - OCR 提取所有文本
  - Presidio 检测: 身份证号, 护照号, 手机号, 邮箱, 银行卡号
  - 脱敏: 替换为 [REDACTED] 或模糊处理图片区域
  │
  ▼
[存入 processed/ bucket] → 后续 Vision LLM 分析使用脱敏后的图片
```

### 6.6.2 视觉幻觉检测

```python
def detect_visual_hallucination(
    vision_result: dict,  # Vision LLM 输出
    ocr_text: str,         # OCR 提取的文本
    image_id: str,
) -> HallucinationReport:
    """
    交叉验证 Vision LLM 的输出与 OCR 文本。

    常见视觉幻觉:
      - LLM 说 "登机口 A12" 但图片上写的是 "Gate B5"
      - LLM 说 "航班号 CA1234" 但图片上是 "MU5678"
      - LLM 自称看到了图片中没有的文字
    """
    claims = extract_claims(vision_result)
    report = HallucinationReport()

    for claim in claims:
        # 在 OCR 文本中搜索证据
        evidence = fuzzy_search(claim, ocr_text)
        if evidence.score < 0.7:
            report.add_hallucination(
                claim=claim,
                severity="high" if evidence.score < 0.3 else "medium",
                suggestion=f"OCR 文本中未找到 '{claim.text}', 可能是幻觉"
            )

    return report
```

### 6.6.3 多模态安全审计

```
audit_multimodal_events 表 (MySQL 月分区):
  event_type: "image_upload" | "image_analysis" | "audio_transcribe"
  user_id, passenger_id,
  resource_id: image_id / audio_id,
  safety_result: JSON (NSFW score, PII detected, redacted fields),
  vision_result_hash: SHA256 (用于后续复核),
  cost: {model, tokens, amount},
  timestamp
```

---

## 6.7 多模态处理管线

### 6.7.1 图片处理管线

```
[客户端] 拍照/选择图片
  │
  ├── 客户端预处理 (可选, 减少带宽):
  │   压缩至 2048px, WebP 格式, 质量 85%
  │   客户端人脸模糊 (推荐)
  │
  ▼
[API Gateway] 接收 multipart/form-data
  │
  ▼
[Image Preprocessor] (同步, <500ms):
  1. 格式验证 (magic bytes)
  2. 尺寸调整 (max 2048px)
  3. 格式统一 (→ WebP, quality 85%)
  4. NSFW 检测 (nudenet, 200ms)
  5. PII 检测 + OCR (Presidio, 300ms)
  6. 生成缩略图 (256px, 用于对话预览)
  │
  ├── [同步路径] Vision LLM 分析 (<3s):
  │   使用脱敏后的图片调用 Vision LLM
  │   → 图片内容理解
  │   → 结构化信息提取 (登机牌/证件)
  │   → 注入 Agent State
  │
  └── [异步路径] 原始图片归档:
      存入 MinIO raw/ bucket
      设置 TTL: 30 天后自动删除
```

### 6.7.2 语音处理管线

```
[客户端] 浏览器麦克风
  │
  ├── VAD (语音活动检测): 检测到语音开始 → 开始录制
  ├── Opus 编码: 压缩音频 (20ms 帧)
  └── WebSocket → 发送音频流

[服务端] WebSocket Handler:
  │
  ├── 接收音频帧 → 缓冲区
  ├── VAD 端点检测: 静音 500ms → 认为一句话结束
  ├── 发送音频片段 → ASR 引擎
  │
  ▼
[ASR 引擎] (<2s):
  ├── Whisper API (OpenAI): 高精度, 按分钟计费
  └── faster-whisper (本地): 零成本, 需 GPU
  │
  ▼
[转写结果] → 注入 State.messages → 正常对话流程

[TTS 输出] (可选, 客户端):
  ├── 浏览器 Web Speech API: 免费, 中文自然
  └── Edge TTS: 微软语音合成, 高质量中文
```

---

## 6.8 多模态 RAG

### 6.8.1 图文联合检索架构

```
用户查询: "登机牌长什么样?"

  ├── 文本嵌入 (text-embedding-3-small) → Milvus text_vectors Collection
  │   返回: 政策文档中关于 "登机牌" 的文本描述 (Top-10)
  │
  ├── 多模态嵌入 (CLIP ViT-L/14) → Milvus image_vectors Collection
  │   返回: 文档中的登机牌示例图片 (Top-5)
  │
  └── RRF 融合 (k=60):
      text_rank × 0.6 + image_rank × 0.4 → Top-5 综合结果
      返回: 文字说明 + 示例图片
```

### 6.8.2 图片分块与嵌入

```
文档 → 解析器 (PDF/Office/HTML)
  │
  ├── 文本部分: 按现有策略分块 → text-embedding → Milvus text_vectors
  │
  └── 图片部分: 提取嵌入图片
      ├── 生成图片描述 (Vision LLM, 异步批量)
      ├── CLIP 嵌入 (图片+文本联合)
      └── 元数据: {parent_doc_id, page_number, caption, surrounding_text}
           → Milvus image_vectors

检索时:
  匹配到的图片 → 返回 {image_url, caption, source_doc, page_number}
  前端渲染: 图片 + 来源标注 + 上下文文本
```

### 6.8.3 多模态 RAG 工具

```python
@tool
def search_multimodal(
    query: str,
    modalities: list[str] = ["text", "image"],
    top_k: int = 5,
) -> ToolResult:
    """
    多模态 RAG 检索 — 同时搜索文本和图片。
    """
    results = {"text": [], "images": []}

    if "text" in modalities:
        text_embedding = get_text_embedding(query)
        results["text"] = milvus_text.search(text_embedding, top_k=top_k)

    if "image" in modalities:
        clip_embedding = get_clip_embedding(query)
        results["images"] = milvus_images.search(clip_embedding, top_k=top_k)

    return ToolResult(status="success", data=results)
```

---

# 第七部分: 非功能性架构

## 7.1 SLO 定义

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

## 7.2 故障模式分析 (FMEA)

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

## 7.3 容量规划模型

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

## 7.4 多租户隔离架构

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

## 7.5 数据隐私合规

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

## 7.6 用户体验度量

| 指标 | 定义 | 目标 |
|------|------|------|
| **任务完成率** | 用户完成预订/改签/取消 | >85% |
| **首次解决率** | 一次对话解决问题 | >70% |
| **对话效率** | 完成任务所需平均轮数 | <5 轮 |
| **降级率** | 转人工比例 | <10% |
| **满意度** | 赞/(赞+踩) | >80% |
| **弃聊率** | 中途放弃比例 | <15% |

## 7.7 多模态非功能性需求

### 7.7.1 多模态 SLO

| 服务 | 可用性 | P95 延迟 | 说明 |
|------|--------|---------|------|
| **图片分析 (Vision LLM)** | 99.5% | <3s | 单张图片内容理解 |
| **图片预处理 (压缩/格式化)** | 99.9% | <500ms | 客户端或服务端预处理 |
| **语音转写 (ASR)** | 99.5% | <2s (首 Token) | Whisper API 或本地模型 |
| **语音合成 (TTS)** | 99.5% | <1s (首音频块) | 客户端优先, 服务端备用 |
| **OCR 文档提取** | 99.0% | <5s | 复杂文档 (多页 PDF/图片) |
| **多模态 RAG 检索** | 99.5% | <1s | CLIP 嵌入 + Milvus 搜索 |
| **图像安全检查 (NSFW/PII)** | 99.9% | <200ms | 上传即检测, 异步确认 |

### 7.7.2 多模态降级路径

```
Level 0: 全模态 (Text + Image + Voice)
Level 1: Text + Image (Voice 不可用 → 纯文本输入)
Level 2: Text Only (Vision LLM 不可用 → 告知 "图片功能暂不可用, 请用文字描述")
Level 3: 仅人机客服 (所有 AI 模态不可用)
```

### 7.7.3 多模态成本模型

| 模态 | 模型 | 成本/单位 | 月预估 (10K 活跃用户) |
|------|------|---------|---------------------|
| **文本** | DeepSeek-Chat | $0.14 / 1M tokens | ~$500 |
| **视觉** | GPT-4o (图片) | $0.00255 / 图片 (1024×1024) | ~$765 (30% 请求含图片) |
| **视觉** | Qwen-VL-Max (迁移后) | ¥0.003 / 千 tokens | ~¥2000 (~$280) |
| **语音 ASR** | Whisper API | $0.006 / 分钟 | ~$180 (10% 请求用语音) |
| **语音 TTS** | Edge TTS (客户端) | 免费 | $0 |
| **嵌入 (文本)** | text-embedding-3-small | $0.02 / 1M tokens | ~$200 |
| **嵌入 (多模态)** | CLIP ViT-L/14 | GPU 自托管或 $0.02/1M tokens | ~$300 |

**综合月成本预估**: $1,500-2,500 (15% 多模态流量 + 85% 纯文本)

### 7.7.4 多模态容量规划

| 资源 | 计算 | 峰值需求 |
|------|------|---------|
| **Vision LLM 并发** | 30% 请求含 1-3 张图片, P95 3s | 50 并发 → 150 TPS 峰值预留 |
| **图片存储 (MinIO)** | 平均 500KB/张, 10K 用户 × 5 张/天 × 365 | ~9TB/年, HOT 层保留 30 天 (~750GB) |
| **音频存储 (审计)** | 平均 50KB/条 (ogg 压缩), 10K × 2 条/天 | ~365GB/年, COLD 归档 |
| **多模态嵌入维度** | CLIP ViT-L: 768 维 × 4 bytes = 3KB/向量 | 100M 图片嵌入 ≈ 300GB 向量存储 |

### 7.7.5 多模态隐私合规

| 要求 | 实现 |
|------|------|
| **图片 PII 检测** | 上传时 Presidio 扩展检测 + OCR 提取文本后脱敏；护照/身份证/登机牌号码自动模糊处理 |
| **人脸保护** | 客户端预模糊 (推荐) 或服务端 MediaPipe 人脸检测 → 高斯模糊 |
| **音频保留策略** | 仅保留转写文本；原始音频保留 7 天后删除 (合规审计用途除外) |
| **图片保留策略** | 对话结束后 30 天自动删除；用户可主动删除 (`DELETE /api/v1/graph/sessions/{id}` 级联删除关联图片) |
| **数据不出境** | 视觉 LLM 优先使用国内 API 端点 (Qwen-VL)；Whisper 使用本地部署版本 |

### 7.7.6 多模态 FMEA 扩展

| 故障 | 爆炸半径 | 降级路径 |
|------|---------|---------|
| **Vision LLM API 不可用** | 所有图片理解请求 | 告知用户 "图片功能暂时不可用, 请用文字描述"；OCR 仍可提取文字 |
| **ASR 服务不可用** | 所有语音输入 | 降级为文本输入；提示用户切换输入方式 |
| **NSFW 检测服务不可用** | 图片上传 | 所有图片请求降级为 "仅 OCR 提取文字", 不进行视觉理解 |
| **MinIO 不可用** | 图片/音频无法存储 | 内存暂存当前会话图片 (限制 5 张 / 20MB)；历史图片不可用 |
| **CLIP 嵌入服务不可用** | 多模态 RAG 检索 | 降级为纯文本 RAG 检索 (图片元数据 + OCR 文本) |

---

# 第八部分: 风险治理与迁移路线图

## 8.1 技术风险登记册

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
| R9 | 视觉 LLM 幻觉导致错误分析 | 高 | 高 | OCR × Vision 交叉验证; 低置信度拒绝回答 | 降级为纯文本 + 告知用户图片分析不可用 |
| R10 | 图片 PII 泄露 (证件照明文存储) | 中 | 高 | 上传即脱敏; 人脸模糊; 30 天 TTL | 拦截所有证件类图片, 仅接受登机牌 |
| R11 | 语音识别准确率不足 (方言/噪音) | 中 | 中 | 置信度过滤; 低置信度转写标注不确定; 降级文本输入 | 提示用户切换文本输入 |
| R12 | 多模态 API 成本失控 | 中 | 中 | Token 预算扩展到多模态 (图片按分辨率折算); 月度预算告警 | 高峰期降级为 GPT-4o-mini 或关闭图片功能 |
| R13 | NSFW 检测误拦正常内容 | 低 | 中 | 阈值可调; 黄灯机制 (标记而非阻断); A/B 测试 | 放行 + 人工复核 |

## 8.2 现状 vs 目标差距矩阵

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
| **多模态输入** | 无 (纯文本) | 图片上传 + 语音输入 | 新增 | P1 |
| **视觉理解** | 无 | Vision LLM (GPT-4o → Qwen-VL) | 新增 | P1 |
| **语音管线** | 无 | ASR (Whisper) + TTS (客户端) | 新增 | P1 |
| **多模态安全** | 无 | 图片 NSFW + PII 脱敏 + 视觉幻觉检测 | 新增 | P1 |
| **多模态 RAG** | 无 | CLIP 嵌入 + 图文联合检索 | 新增 | P2 |
| **前端多模态** | 无 | 图片上传预览 + 语音按钮 + 多模态渲染 | 新增 | P1 |

## 8.3 分阶段迁移路线图

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

### Phase 10a: 多模态基础能力 (6-8 天)

| 步骤 | 内容 | 优先级 |
|------|------|--------|
| M1.1 | `app/core/config.py` 增加多模态配置字段 (视觉模型/图片参数/语音参数) | P1 |
| M1.2 | `AbstractLLMProvider` 扩展 `get_vision_model()` 接口 | P1 |
| M1.3 | `OpenAIProvider` 实现 `get_vision_model()` → GPT-4o | P1 |
| M1.4 | `VisionPreprocessor` 实现 (格式验证/压缩/尺寸调整) | P1 |
| M1.5 | `ImageSafetyChecker` 实现 (NSFW 检测 + PII 脱敏) | P1 |
| M1.6 | MinIO 多模态 Bucket 创建 (images/raw, images/processed, images/thumbnails, audio/) | P1 |
| M1.7 | `app/api/v1/graph/chat/multimodal` 端点 (multipart/form-data) | P1 |
| M1.8 | 前端 `ImagePreview` + `ChatInput` 图片上传组件 | P1 |
| M1.9 | 前端 `MessageBubble` 多模态内容渲染 | P1 |

### Phase 10b: 多模态 Agent 集成 (5-7 天)

| 步骤 | 内容 | 优先级 |
|------|------|--------|
| M2.1 | `ModalityDetector` 节点 (规则引擎, 检测图片/音频/文本) | P1 |
| M2.2 | `vision_analyzer` 节点 (Vision LLM 理解 + OCR) | P1 |
| M2.3 | `parse_boarding_pass` 工具 (登机牌结构化提取) | P1 |
| M2.4 | `analyze_image` 工具 (通用图片理解) | P1 |
| M2.5 | `extract_document_text` 工具 (OCR 文档提取) | P1 |
| M2.6 | `IntentClassifier` 扩展图片意图 (登机牌→flight, 证件→primary, ...) | P1 |
| M2.7 | Primary Agent 多模态 System Prompt 更新 | P1 |
| M2.8 | `MultimodalAgent` 基类 (预处理钩子) | P2 |

### Phase 10c: 语音能力 (4-5 天)

| 步骤 | 内容 | 优先级 |
|------|------|--------|
| M3.1 | `AbstractASRProvider` + `WhisperAPIProvider` 实现 | P1 |
| M3.2 | WebSocket `/api/v1/graph/chat/voice` 端点 | P1 |
| M3.3 | `audio_transcriber` 节点 (ASR 转写 → 注入 State) | P1 |
| M3.4 | `transcribe_audio` 工具 | P2 |
| M3.5 | 前端 `VoiceInput.vue` 组件 (VAD + Opus + WebSocket) | P1 |
| M3.6 | 客户端 TTS 集成 (Web Speech API / Edge TTS) | P2 |

### Phase 10d: 多模态 RAG + 安全深度 (5-7 天)

| 步骤 | 内容 | 优先级 |
|------|------|--------|
| M4.1 | CLIP 嵌入服务部署 (本地 GPU 或 API) | P2 |
| M4.2 | Milvus `image_vectors` Collection 创建 | P2 |
| M4.3 | `search_multimodal` 工具 (图文联合检索) | P2 |
| M4.4 | 视觉幻觉检测 (OCR × Vision 交叉验证) | P1 |
| M4.5 | 多模态安全审计表 (`audit_multimodal_events`) | P2 |
| M4.6 | 图片保留策略 (TTL 30 天, 用户可删除) | P2 |
| M4.7 | 多模态 E2E 测试 (上传登机牌 → 自动查询航班) | P1 |

**多模态预计工期**: M1-M4 总计 20-27 天 (与核心 Phase 0-10 部分并行)

**预计总工期**: Phase 0-6 核心交付 18-25 天, Phase 7-10 完整交付 38-51 天, 多模态 M1-M4 额外 20-27 天

---

# 第九部分: 部署与运维

## 9.1 Docker Compose 拓扑

```yaml
services:
  nginx:       # 反向代理 (80/443, WebSocket 支持 for 语音)
  app:         # FastAPI (8000) — 多模态 API
  mysql:       # MySQL 8.0 (3306) — 业务数据
  postgres:    # PostgreSQL 16 (5432) — Agent 记忆
  redis:       # Redis 7 (6379) — 缓存 + 限流 + 队列
  qdrant:      # Qdrant (6333) — 文本向量存储 (≤10TB)
  # Phase 7 扩展:
  # milvus-proxy, milvus-querynode × 8, milvus-datanode × 3
  # milvus-indexnode × 2, etcd, pulsar
  # minio × 8 (分布式)
  # Phase 10a 多模态扩展:
  whisper:     # faster-whisper (本地 ASR, GPU 可选)
  clip:        # CLIP 嵌入服务 (GPU Node, Phase 10d)
```

## 9.2 高可用拓扑

```
FastAPI (K8s, HPA: 3-20 Pods)
  │
  ├── MySQL: ProxySQL (读写分离) + Orchestrator (故障转移)
  ├── PostgreSQL: PgBouncer (连接池) + HAProxy + Patroni (HA)
  ├── Redis: Sentinel (1主+2从+3哨兵)
  └── Milvus: 3 副本
```

## 9.3 监控告警体系

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

## 9.4 测试体系

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
| `presidio-image-redactor` | 图片 PII 脱敏 | M1 |
| `Pillow` | 图片处理 (压缩/格式转换) | M1 |
| `python-multipart` | multipart/form-data 解析 | M1 |
| `openai-whisper` 或 `faster-whisper` | 语音转写 (本地) | M3 |
| `opuslib` | Opus 音频编解码 | M3 |
| `websockets` | WebSocket 语音支持 | M3 |
| `nudenet` 或 `transformers[safety]` | 图片 NSFW 检测 | M1 |
| `openai-clip` 或 `transformers[clip]` | CLIP 多模态嵌入 | M4 |

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
| **视觉 LLM** | GPT-4o / Qwen-VL-Max | 图片内容理解 + OCR |
| **语音 ASR** | Whisper (API) / faster-whisper (本地) | 语音转文字 |
| **语音 TTS** | Web Speech API / Edge TTS / OpenAI TTS | 文字转语音 |
| **多模态嵌入** | CLIP ViT-L/14 / Chinese-CLIP | 图文联合检索 |
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

# 第十部分: 前端架构设计

## 10.1 技术栈

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
| @ricky0123/vad-web | ^0.x | 客户端语音活动检测 (VAD) |
| opus-media-recorder | ^0.x | Opus 编码录音 |
| compressorjs | ^1.x | 客户端图片压缩 |
| dompurify | ^3.x | XSS 防护 (含图片 SVG 过滤) |

## 10.2 路由设计

```
/                  → ChatPage       (需登录)
  /login           → LoginPage      (游客)
  /admin           → AdminPage       (需登录)
    /admin/        → Dashboard      (概览仪表盘)
    /admin/users   → Users          (用户管理)
    /admin/conversations → Conversations (对话监控)
    /admin/documents   → Documents  (文档管理)
```

## 10.3 组件树

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

## 10.4 状态管理 (Pinia)

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

## 10.5 数据流

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

## 10.6 SSE 流式处理

```
fetch() → ReadableStream reader
  → 按 \n 分割数据行
  → 解析 data: {...} JSON
  → {content} → 更新消息气泡 (逐字显示)
  → {thread_id} → 保存会话 ID
  → AbortController 支持取消
```

## 10.7 预订卡片设计

Agent 返回的预订结果渲染为可视化卡片:

**FlightCard**: 蓝色左边框, 飞机图标, 出发→到达 (机场代码), 日期时间, 航班号, 舱位

**HotelCard**: 橙色左边框, 建筑图标, 酒店名称, 位置, 入住/退房日期, 价格层级

**CarRentalCard**: 绿色左边框, 汽车图标, 租车公司, 地点, 起止日期

## 10.8 管理后台

**Dashboard**: 5 个统计卡片 (用户数/对话数/Token/费用/日活)

**Users**: 用户列表表格 (ID/用户名/手机/姓名), 搜索, 分页

**Conversations**: 对话监控列表 (会话ID/用户/消息数/时间/状态)

**Documents**: RAG 文档管理 (上传区/文档列表/状态/操作)

## 10.9 部署

**开发环境**: Vite dev server (:5173) → proxy /api → FastAPI (:8000)

**生产环境**: `vite build` → `dist/` → Nginx 静态文件 + /api 反代

```
Nginx:
  /           → frontend/dist/   (静态文件)
  /api/       → app:8000         (FastAPI 后端)
  /api/graph/chat → SSE 支持    (proxy_buffering off)
  ws://       → app:8000         (WebSocket 语音)
```

### 10.10 多模态 UI 组件

#### 10.10.1 图片上传组件

```
ChatInput.vue 扩展:
  ├── 文本输入 (原有, auto-resize)
  ├── 📎 附件按钮:
  │   ├── 上传图片 (点击 → 文件选择器)
  │   │   支持: 拍照 / 相册 / 拖拽上传
  │   │   限制: 最多 5 张, 单张 ≤20MB, JPEG/PNG/WebP
  │   ├── 语音按钮 (长按录音)
  │   └── 发送按钮
  └── 上传预览区:
      显示已选图片缩略图 (256px), 可删除单张
```

**ImagePreview.vue** (新增):
```
图片缩略图网格:
  ├── 图片缩略图 (128px, object-fit: cover)
  ├── 删除按钮 (×)
  ├── 上传进度条 (上传中)
  └── 安全检查状态: ✓ 通过 / ⚠️ 脱敏 / ✗ 拒绝
```

**MessageBubble.vue 扩展 — 图片消息**:
```
用户消息气泡:
  ├── 文本内容 (如有)
  └── 图片展示:
      ├── 缩略图 (256px) → 点击展开大图 (Lightbox)
      └── 图片标签: "登机牌" / "证件" / "行程单" (AI 自动识别)
```

#### 10.10.2 语音输入组件

**VoiceInput.vue** (新增):
```
语音按钮 UI:
  ├── 默认状态: 🎤 灰色图标
  ├── 按压中: 🎤 红色脉冲动画 + "正在聆听..."
  ├── 处理中: ⏳ "识别中..."
  └── 完成: 转写文本显示在输入框

技术实现:
  ├── MediaRecorder API (浏览器原生)
  ├── VAD: @ricky0123/vad-web (客户端语音活动检测)
  ├── Opus 编码: 降低带宽
  ├── WebSocket: ws://host/api/v1/graph/chat/voice
  └── 降级: WebSocket 不可用 → 回退到 HTTP multipart 上传录音文件
```

#### 10.10.3 AI 回复中的多模态内容渲染

**MessageBubble.vue 扩展 — 多模态回复渲染**:
```
AI 回复中可能包含:
  ├── Markdown 文本 (原有)
  ├── 预订卡片 (原有: FlightCard, HotelCard, CarRentalCard)
  ├── 图片引用 (新增):
  │   [image:boarding_pass_sample_01] → 渲染为可点击的示例图片
  ├── 置信度指示器 (新增):
  │   文字分析: 🟢 高置信度
  │   图片分析: 🟡 中置信度 (OCR 与 Vision 结果不完全一致)
  │   建议: 人工核实关键信息
  └── 多模态分析结果卡片 (新增):
      VisionAnalysisCard: 结构化展示图片分析结果
      例: 登机牌识别 → {航班号, 日期, 登机口, 座位号} 表格展示
```

#### 10.10.4 客户端图片预处理

```typescript
// utils/imagePreprocessor.ts
export async function preprocessImage(file: File): Promise<ProcessedImage> {
  // 1. 格式验证
  const allowedTypes = ['image/jpeg', 'image/png', 'image/webp'];
  if (!allowedTypes.includes(file.type)) {
    throw new Error('不支持的图片格式');
  }

  // 2. 大小检查
  if (file.size > 20 * 1024 * 1024) {
    throw new Error('图片大小不能超过 20MB');
  }

  // 3. 客户端压缩 (Canvas API)
  const compressed = await compressImage(file, {
    maxDimension: 2048,
    format: 'webp',
    quality: 0.85,
  });

  // 4. 生成缩略图 (256px)
  const thumbnail = await compressImage(file, {
    maxDimension: 256,
    format: 'webp',
    quality: 0.7,
  });

  return { compressed, thumbnail };
}
```

#### 10.10.5 前端多模态数据流

```
SSE 流式对话 (多模态扩展):
  用户上传图片 + 输入文本
    → ChatInput.vue → preprocessImage() (客户端压缩)
    → POST /api/v1/graph/chat/multimodal (multipart/form-data)
    → chatStore.addMessage(user msg with images[])
    → SSE events:
      event: modality → {type: "image_analysis", status: "analyzing"}
      event: tool_call → {tool: "parse_boarding_pass", ...}
      event: token → {content: "您的登机牌信息如下..."}
      event: done → {session_id, modalities_used: ["text", "image"]}
    → MessageBubble 渲染: 文本 + VisionAnalysisCard

---

> **文档维护**: 本文件是项目唯一权威架构文档，所有架构决策必须在此文档中体现。代码变更前请先更新此文档。
