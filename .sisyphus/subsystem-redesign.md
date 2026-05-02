# 核心子系统重新设计方案

> **版本**: v1.0  
> **日期**: 2026-04-28  
> **关联文档**: `upgrade-architecture.md`  
> **设计原则**: 架构先行 / 设计优先 / 权衡可见  

---

## 目录

1. [RAG 系统重设计](#1-rag-系统重设计)
2. [记忆与检查点机制重设计](#2-记忆与检查点机制重设计)
3. [跨 Agent 用户身份统一设计](#3-跨-agent-用户身份统一设计)
4. [城市映射数据库化设计](#4-城市映射数据库化设计)
5. [子系统集成架构](#5-子系统集成架构)

---

## 1. RAG 系统重设计

### 1.1 现状诊断

| 维度 | 现状 | 根因 |
|------|------|------|
| 向量存储 | numpy 内存数组，重启丢失 | 无持久化向量数据库 |
| 文档分块 | 正则 `split(r"(?=\n##)")`，无视段落边界 | 无专用分块器，无语义感知 |
| 嵌入计算 | 每次重启全量重算 | 无增量索引，无缓存 |
| 检索精度 | 暴力点积 top-k，无重排序 | 无混合搜索，无 MMR |
| 密钥管理 | API Key 硬编码源码 | 无密钥生命周期管理 |
| 文档更新 | 需重启进程 | 无热更新，无版本追踪 |

### 1.2 目标架构

```
                        ┌──────────────────────────────┐
                        │     Ingestion Pipeline        │
                        │                               │
 order_faq.md ──────▶  MarkdownHeaderTextSplitter       │
 (Markdown, 中文FAQ)     ├─ 按 ## 保留标题元数据        │
                         └─ 产生粗粒度 section docs      │
                                 │                       │
                                 ▼                       │
                        RecursiveCharacterTextSplitter   │
                        ├─ chunk_size=512 (中文字符)     │
                        ├─ chunk_overlap=100 (20%)      │
                        └─ separators: 。！？；，、\n    │
                                 │                       │
                                 ▼                       │
                        LangChain Indexing API           │
                        ├─ SQLRecordManager (变更追踪)  │
                        ├─ cleanup="incremental"        │
                        └─ 产出 ~80-150 语义完整分块     │
                                 │                       │
                                 ▼                       │
                        ┌──────────────────────┐        │
                        │   Qdrant (Docker)    │        │
                        │   collection:        │        │
                        │   travel_faq         │        │
                        │   ├─ 768维 dense     │        │
                        │   └─ (预留)BM25稀疏  │        │
                        └──────────────────────┘        │
                        └──────────────────────────────┘

                        ┌──────────────────────────────┐
                        │     Retrieval Pipeline        │
                        │                               │
 lookup_policy(query) ──▶  Qdrant 相似度搜索 (k=20)   │
                                  │                      │
                          ┌───────┴───────┐              │
                          │  (预留)       │              │
                          │  Cohere       │              │
                          │  rerank-      │              │
                          │  multilingual │              │
                          │  v3.0         │              │
                          │  k=20 → k=5   │              │
                          └───────┬───────┘              │
                                  │                      │
                                  ▼                      │
                         ┌────────────────┐              │
                         │  返回 top-k    │              │
                         │  + metadata    │              │
                         │  (section,     │              │
                         │   similarity)  │              │
                         └────────────────┘              │
                        └──────────────────────────────┘
```

### 1.3 核心架构决策

#### ADR-R1: 向量存储选型

| 候选 | 部署模式 | 混合搜索 | 中文友好 | 自托管 | 决策 |
|------|----------|----------|----------|--------|------|
| Qdrant | Docker 单容器 | ✅ BM25 + Dense | ✅ | ✅ 免费 | **选用** |
| pgvector | PG 扩展 | ✅ pg_search | ✅ | ✅ | 备选（需额外 PG 实例） |
| ChromaDB | 嵌入/独立 | ⚠️ 有限 | ✅ | ✅ | 不选（大规模性能差） |
| Pinecone | 纯 SaaS | ✅ | ✅ | ❌ | 不选（不可自托管） |

**选择 Qdrant 的理由**:
- Rust 实现，单容器 1GB 内存可运行数万向量
- 原生支持 BM25 + Dense 混合搜索（v1.7+）
- LangChain `langchain-qdrant` 一等集成
- Docker Compose 一行部署，不引入新数据库实例

#### ADR-R2: 中文分块策略

| 参数 | 取值 | 设计理由 |
|------|------|----------|
| 分隔符优先级 | `\n\n` → `\n` → `。！？` → `；` → `，、` | 中文无空格天然分隔，需句末标点优先 |
| chunk_size | **512 字符** | 适配 text-embedding-3-small 上下文，单 chunk 约 200-300 tokens |
| chunk_overlap | **100 字符 (20%)** | FAQ 政策条款前后引用多，需较高重叠比 |
| 双层分块 | MarkdownHeader + RecursiveCharacter | 保留标题结构用于溯源 + 细粒度控制语义完整性 |

**为什么不用 SemanticChunker**: FAQ 天然带编号列表和标题，边界清晰。SemanticChunker 需额外调用 embedding 模型检测语义边界，对当前场景性价比低。

#### ADR-R3: 嵌入模型演进路线

```
Phase 1 (当前)          Phase 2 (稳定后)
text-embedding-3-small  →  BGE-large-zh-v1.5 (自托管)
├─ 维度: 768              ├─ 维度: 1024
├─ 中文 MTEB: ~72%        ├─ 中文 C-MTEB: 64.53
├─ 延迟: 340ms            ├─ 延迟: ~50ms
├─ 成本: $0.02/1M tokens  ├─ 成本: 免费
└─ 依赖: OpenAI API        └─ 依赖: 本地 Docker
```

**切换门槛**: 文档量 >500 条分块 或 日均查询 >1000 次时触发 Phase 2。

#### ADR-R4: 重排序策略

**当前阶段: 不启用**。FAQ 分块后约 80-150 条，向量 top-k 精度足够。

**预留接口**: 当分块量 >500 时，激活二阶段检索：

| 阶段 | 操作 | 参数 |
|------|------|------|
| First-pass | Qdrant 相似度搜索 | k=20 |
| Second-pass | Cohere rerank-multilingual-v3.0 | k=20 → top_n=5 |

**备选自托管方案**: `BAAI/bge-reranker-v2-m3` cross-encoder。

#### ADR-R5: 文档更新机制

**核心方案**: LangChain Indexing API + SQLRecordManager。

```
文档变更检测流程:
  order_faq.md (文件) 
    → 计算内容哈希 (MD5)
    → 与 SQLRecordManager 记录比对
    → 识别: 新增 / 修改 / 删除 的分块
    → 仅处理变更部分
    → 更新 Qdrant + 更新 RecordManager
```

**关键参数 `cleanup="incremental"`**: 仅删除同一 source_id 的旧版本，保留不相关文档。

### 1.4 数据流

```
[启动时/定时]
  order_faq.md → 分块管线 → Qdrant (增量同步)

[运行时 - Agent 工具调用]
  lookup_policy("如何退票?")
    → Qdrant.search(query_embedding, k=5)
    → 返回 top-5 文档 + metadata
    → 拼接为 LLM 上下文
    → 注入 primary_assistant prompt
```

### 1.5 LangGraph 集成模式

RAG 不内联为图节点，保持为 **Agent Tool**：

```
primary_assistant
  ├─ 判断需要查政策 → 调用 lookup_policy tool
  │     └─ ToolNode 执行 → 返回检索结果
  ├─ 结果注入对话上下文
  └─ LLM 基于检索结果生成回答
```

**关键设计**: Agent 自主决定何时检索，而非每个请求都触发 RAG。避免不必要开销。

---

## 2. 记忆与检查点机制重设计

### 2.1 现状诊断

| 维度 | 现状 | 根因 |
|------|------|------|
| 检查点存储 | MemorySaver (进程内 SQLite) | 重启幸存但多进程不安全 |
| 长对话处理 | 无截断、无摘要 | 上下文窗口溢出风险 |
| 跨会话记忆 | 无 | 每次对话从零开始 |
| 会话恢复 | 依赖 thread_id，无用户绑定 | 无法按用户查询历史会话 |
| 数据保留 | 无限增长 | 无 GC 策略 |

### 2.2 三层记忆架构

```
┌─────────────────────────────────────────────────────────────┐
│                     记忆架构 (三层)                           │
│                                                              │
│  ┌───────────────────────────────────────────────────────┐  │
│  │ Layer 1: 短期记忆 (Per-Turn)                           │  │
│  │ State.messages (LangGraph State 内)                    │  │
│  │ ─ 生命周期: 单次图执行                                  │  │
│  │ ─ 管理: add_messages reducer                           │  │
│  │ ─ 摘要触发: >2048 tokens → SummarizationNode 压缩      │  │
│  └───────────────────────────────────────────────────────┘  │
│                          │                                   │
│                          ▼                                   │
│  ┌───────────────────────────────────────────────────────┐  │
│  │ Layer 2: 会话记忆 (Per-Session)                        │  │
│  │ PostgresSaver Checkpoint                               │  │
│  │ ─ 生命周期: 单次对话会话                                │  │
│  │ ─ 持久化: 每个节点执行后写入 PostgreSQL                 │  │
│  │ ─ 恢复: 通过 thread_id 重建完整对话状态                 │  │
│  │ ─ 保留策略: TTL 30天, 保留最近 20 checkpoint/thread    │  │
│  └───────────────────────────────────────────────────────┘  │
│                          │                                   │
│                          ▼                                   │
│  ┌───────────────────────────────────────────────────────┐  │
│  │ Layer 3: 长期记忆 (Cross-Session)                      │  │
│  │ PostgresStore                                          │  │
│  │ ─ 生命周期: 跨会话持久                                  │  │
│  │ ─ 命名空间: (domain, user_id) → preferences/profile    │  │
│  │ ─ 内容: 用户偏好、历史行程摘要、常用目的地              │  │
│  │ ─ 更新: 每次对话结束后 LLM 提取关键信息                 │  │
│  └───────────────────────────────────────────────────────┘  │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

### 2.3 核心架构决策

#### ADR-M1: 检查点后端

| 候选 | 持久化 | 并发安全 | LangGraph 官方 | 决策 |
|------|--------|----------|---------------|------|
| MemorySaver | ❌ | ❌ | ✅ | 仅开发 |
| SqliteSaver | ✅ | ❌ 单写入者 | ✅ | 单 worker |
| PostgresSaver | ✅ | ✅ 连接池 | ✅ | **选用** |
| langgraph-checkpoint-mysql | ✅ | ⚠️ 社区版 | ❌ 非官方 | 不选 |

**选择 PostgresSaver 的理由**:
- LangGraph 官方维护，有完整迁移系统
- 连接池 + 并发安全 + JSONB 索引
- pipeline 模式优化批量写入
- Docker Compose 增加一个 PostgreSQL 容器即可

**MySQL 约束说明**: 项目统一使用 MySQL 存储业务数据。但 LangGraph checkpoint 的官方生产实现是 PostgreSQL。推荐方案是在 docker-compose 中增加一个轻量 PostgreSQL 实例专用于 checkpoint + long-term store，与业务 MySQL 分离。

#### ADR-M2: 对话摘要策略

**触发机制**: 基于 token 计数而非消息条数。

```
对话 token 数 > 2048 → SummarizationNode 触发
  ├─ 提取最近对话摘要 (max 256 tokens)
  ├─ 合并旧摘要 + 新轮次 → 形成运行摘要
  └─ LLM 仅看到: 摘要 + 最近 N 轮完整消息
```

**设计要点**:
- 摘要节点作为图的第一个节点（在 LLM 调用之前）
- 分离两条消息流：`messages`(完整历史, 用于 UI 展示) vs `summarized_messages`(压缩后, 用于 LLM)
- 摘要模型使用更便宜/快速的 LLM（如 gpt-4o-mini）

#### ADR-M3: 长期记忆提取

**时机**: 每次对话正常结束后（非中断）。

**提取模式**:
```
对话结束 → LLM 提取结构化信息
  ├─ 用户偏好: 座位偏好(靠窗/过道)、舱位偏好、酒店星级偏好
  ├─ 常去目的地: 最近 5 次查询的城市
  ├─ 历史操作: 最近改签/取消记录
  └─ 写入 PostgresStore, key=(users, user_id).preferences
```

**写入策略**:
- **可变属性** (如 preferences): 使用 `store.put()` 覆盖写
- **追加属性** (如行程历史): 使用 `store.put()` 带时间戳 key

#### ADR-M4: 检查点保留策略

| 策略 | 参数 | 说明 |
|------|------|------|
| 时间 TTL | 30 天 | 超过 30 天的 checkpoint 删除 |
| 数量限制 | 保留最近 20 个/thread | 防止单线程无限膨胀 |
| 提取优先 | GC 前提取关键信息到 Store | 保留有用信息，删除冗余 |
| 定时执行 | 每日凌晨 CronJob | 业务低峰期执行 |

### 2.4 对话生命周期

```
[用户发起对话]
  POST /api/v1/graph/chat (thread_id=null)
    → 创建新 thread_id = f"user_{user_id}:{uuid}"
    → 加载长期记忆 (PostgresStore)
    → 注入到 graph State

[多轮对话中]
  每轮:
    1. SummarizationNode (检查是否需要压缩)
    2. Agent 路由 + 工具调用
    3. Checkpoint 自动写入 (每个节点)
    4. Human-in-the-loop 中断 (敏感工具前)

[对话结束]
  LLM 判断任务完成 → extract_memories 节点
    → 提取偏好和行程摘要
    → 写入 PostgresStore
    → Graph 返回 END

[会话恢复]
  GET /api/v1/graph/sessions?user_id=X
    → 列出活跃 thread_id
  POST /api/v1/graph/chat (thread_id=existing)
    → PostgresSaver 恢复状态
    → 继续对话
```

### 2.5 配置拓扑

```
docker-compose.yml:
  postgres:
    image: postgres:16-alpine
    environment:
      POSTGRES_DB: langgraph
      POSTGRES_USER: langgraph
      POSTGRES_PASSWORD: ${PG_PASSWORD}
    ports: ["5432:5432"]
    volumes: ["pg_data:/var/lib/postgresql/data"]

graph.compile(
    checkpointer=PostgresSaver(pg_pool),  # Layer 2: 会话记忆
    store=PostgresStore(pg_conn),         # Layer 3: 长期记忆
    interrupt_before=[...],               # Human-in-the-loop
)
```

---

## 3. 跨 Agent 用户身份统一设计

### 3.1 现状诊断

| 维度 | 现状 | 根因 |
|------|------|------|
| API 认证 | JWT 验证完成，username 存入 request.state | 但从未传递给图 |
| passenger_id | 硬编码 `"3442 587242"`，API 请求体自由传入 | 无验证、无绑定 |
| 用户↔乘客映射 | 不存在 | MySQL UserModel 无 passenger_id 字段 |
| 工具权限 | 仅航班工具有 ownership 检查；酒店/租车/行程无 | `config` 参数未传递 |
| 审计追踪 | 无 | 无用户级操作记录 |

### 3.2 目标架构

```
┌──────────────────────────────────────────────────────────────┐
│                   身份传播全链路                               │
│                                                               │
│  ┌──────────┐    ┌──────────────┐    ┌───────────────────┐   │
│  │  HTTP    │───▶│  FastAPI     │───▶│  LangGraph        │   │
│  │  Bearer  │    │  Middleware  │    │  Graph Execution  │   │
│  │  JWT     │    │              │    │                   │   │
│  └──────────┘    └──────┬───────┘    └────────┬──────────┘   │
│                         │                      │              │
│                    ┌────▼─────┐          ┌─────▼──────┐      │
│                    │ JWT 解码 │          │ Runtime    │      │
│                    │ user_id  │─────────▶│ Context    │      │
│                    │ username │  注入     │ (UserCtx)  │      │
│                    └──────────┘          └─────┬──────┘      │
│                                               │              │
│                          ┌────────────────────┼──────┐       │
│                          │                    │      │       │
│                     ┌────▼────┐  ┌─────────┐  │  ┌──▼────┐  │
│                     │ 图节点   │  │ 子Agent │  │  │ 工具  │  │
│                     │ Runtime │  │ Runtime │  │  │ToolRt │  │
│                     │[UserCtx]│  │[UserCtx]│  │  │[UCTX] │  │
│                     └─────────┘  └─────────┘  │  └───────┘  │
│                                               │              │
│                    用户信息在所有节点/工具中   │              │
│                    自动可用，无需手动传递      │              │
│                                               │              │
└───────────────────────────────────────────────┴──────────────┘
```

### 3.3 核心架构决策

#### ADR-I1: 身份注入机制

**方案对比**:

| 方案 | 原理 | 侵入性 | 类型安全 | 决策 |
|------|------|--------|----------|------|
| RunnableConfig 透传 | `config.configurable.passenger_id` | 低 | ❌ | 向后兼容 |
| State 显式字段 | `state["user_id"]` | 中 | ⚠️ | 状态污染 |
| Runtime Context 注入 | `runtime: Runtime[UserContext]` | 中 | ✅ | **选用** |

**选择 Runtime Context 的理由**:
- LangGraph 1.0 原生机制，框架级自动注入
- 类型安全（`Runtime[UserContext]`）
- **不写入 checkpoint**（避免 PII 泄漏到持久化状态）
- 对节点和工具统一适用（`Runtime` / `ToolRuntime`）

#### ADR-I2: 身份上下文定义

```
UserContext (注入到 Runtime):
  ├─ user_id: int           # JWT → UserModel.id
  ├─ username: str          # JWT → UserModel.username
  ├─ passenger_id: str      # UserModel → 映射表 → passenger_id
  └─ real_name: str|null    # 用户真实姓名

注入链路:
  API 层 (graph_views.py):
    request.state.username → 解析 user_id
    → 查询 user→passenger 映射表
    → 构建 UserContext
    → graph.stream(..., context=UserContext(...))
  
  图执行层 (自动):
    LangGraph 识别节点签名中的 Runtime[UserContext]
    → 自动注入到所有节点/工具
```

#### ADR-I3: API 层身份桥接

```
POST /api/v1/graph/chat:
  1. Middleware: 验证 JWT → request.state.username
  2. 解析: "1:alice" → user_id=1, username="alice"
  3. 查找映射: user_id → passenger_id (MySQL user_passenger_mapping)
  4. 校验: 如请求体提供了 passenger_id，必须与映射结果一致
  5. 构建 Runtime Context
  6. 构建 thread_id = "user_{user_id}:{uuid}"
  7. graph.stream(input, config, context=UserContext(...))
```

**关键变更**: 移除 API 请求体中的 `passenger_id` 字段 —— 身份只能从 JWT 派生，不可由客户端指定。

#### ADR-I4: 工具层所有权强制

所有写操作工具必须接受并验证用户身份：

| 工具 | 当前 | 新设计 |
|------|------|--------|
| `book_hotel(hotel_id)` | 无身份检查 | `book_hotel(hotel_id, runtime: ToolRuntime[UserContext])` → 记录操作者 |
| `cancel_hotel(hotel_id)` | 无身份检查 | 同上 |
| `book_car_rental(rental_id)` | 无身份检查 | 同上 |
| `cancel_car_rental(rental_id)` | 无身份检查 | 同上 |
| `book_excursion(id)` | 无身份检查 | 同上 |
| `update_ticket_to_new_flight(...)` | ✅ 有检查 | 保持，改用 ToolRuntime |
| `cancel_ticket(...)` | ✅ 有检查 | 保持，改用 ToolRuntime |

#### ADR-I5: 多租户隔离

```
隔离层次:
  1. thread_id 命名空间: "user_{user_id}:{uuid}"
     → 不同用户的 thread_id 天然不同，无法交叉恢复
  
  2. 业务数据查询隔离:
     WHERE passenger_id = runtime.context.passenger_id
     → 所有工具查询强制过滤
  
  3. 检查点隔离:
     PostgresSaver 按 thread_id 索引
     → 用户 A 无法读取用户 B 的 thread 状态
```

#### ADR-I6: 审计追踪

```
审计记录结构:
  {
    event_type: "tool_call",
    timestamp: UTC ISO 8601,
    user_id: int,
    passenger_id: str,
    tool_name: str,
    params: dict (PII 已脱敏),
    result_status: "success" | "denied" | "error",
    thread_id: str,
  }

存储: 专用 audit_events 表 (MySQL) + 应用日志
PII 脱敏: 密码/证件号等字段自动替换为 [REDACTED]
```

### 3.4 用户↔乘客映射表设计

```sql
-- 方案 A: 一对一映射 (推荐，业务场景: 一个登录用户对应一个旅客)
ALTER TABLE t_user ADD COLUMN passenger_id VARCHAR(50);
CREATE INDEX idx_user_passenger ON t_user(passenger_id);

-- 方案 B: 多对多映射 (扩展场景: 一个用户管理多个旅客)
CREATE TABLE user_passenger_mapping (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL,
    passenger_id VARCHAR(50) NOT NULL,
    is_default BOOLEAN DEFAULT FALSE,
    FOREIGN KEY (user_id) REFERENCES t_user(id),
    UNIQUE KEY (user_id, passenger_id)
);
```

**推荐方案 A**，预留方案 B 的迁移路径。

---

## 4. 城市映射数据库化设计

### 4.1 现状诊断

| 维度 | 现状 | 根因 |
|------|------|------|
| 数据规模 | 8 个城市（5 中国 + 2 瑞士 + 1 其他） | 硬编码字典 |
| 中文检测 | 逐字判断 Unicode 范围 | CJK 范围不完整 |
| 模糊匹配 | 无 | 变体（"北京市"/"北京"）无法匹配 |
| IATA 代码 | 不支持 | 无法按机场代码搜索 |
| 数据源 | 代码内 | 不可动态维护 |

### 4.2 目标架构

```
                    ┌─────────────────────────┐
                    │   cities 表 (MySQL)      │
                    │                          │
                    │  id: INT PK              │
                    │  name_zh: VARCHAR (北京) │
                    │  name_en: VARCHAR (Beijing)│
                    │  name_aliases: JSON      │
                    │    ["北京市","Peking"]   │
                    │  iata_code: VARCHAR (PEK)│
                    │  country: VARCHAR        │
                    │  timezone: VARCHAR       │
                    │  is_active: BOOLEAN      │
                    └──────────┬──────────────┘
                               │
          ┌────────────────────┼────────────────────┐
          │                    │                    │
    精确匹配              模糊匹配             IATA 查询
    name_zh / name_en    name_aliases LIKE     iata_code =
    = 用户输入           %用户输入%            用户输入
          │                    │                    │
          └────────────────────┼────────────────────┘
                               │
                               ▼
                    ┌─────────────────────┐
                    │  CityMapperService  │
                    │  ├─ resolve(query)  │
                    │  ├─ 缓存热点查询    │
                    │  └─ 返回标准化名称  │
                    └─────────────────────┘
```

### 4.3 核心架构决策

#### ADR-C1: 存储方案

| 方案 | 数据维护 | 查询性能 | 扩展性 | 决策 |
|------|----------|----------|--------|------|
| 代码字典 | 需发版 | N/A | ❌ | 废弃 |
| 配置文件 | 需发版 | N/A | ❌ | 废弃 |
| MySQL 表 | 在线增删改 | 索引查询 | ✅ | **选用** |
| Redis 缓存层 | 需同步 | 极高 | ✅ | 预留 |

**选用 MySQL 表**: 利用现有 MySQL 实例，无新增依赖。城市数据量小（预计 < 500 行），索引查询延迟 < 1ms。

#### ADR-C2: 模糊匹配选型

**当前阶段不需要引入模糊匹配库（如 fuzzywuzzy）**。理由：
- 城市名称变体有限，通过 `name_aliases` JSON 数组覆盖即可
- 模糊匹配库引入额外依赖和计算开销
- 如 `aliases` 不匹配，LLM 本身具备语义理解能力，可在对话中澄清

**预留方案**: 当城市数据 > 200 条且变体匹配失败率 > 5% 时，引入 `thefuzz` 进行 token_sort_ratio 模糊匹配。

#### ADR-C3: 缓存策略

```
查询流程:
  1. 检查应用内存 LRU Cache (maxsize=200, ttl=1h)
     → 命中 → 返回
     → 未命中 → 查 DB

  2. DB 查询:
     SELECT name_en FROM cities
     WHERE name_zh = ? OR name_en = ? OR JSON_CONTAINS(name_aliases, ?) OR iata_code = ?
     LIMIT 1
    
  3. 写入 Cache
     → 返回标准化英文名称
```

**为什么不用 Redis**: 城市查询是低频操作（每轮对话至多 1-2 次），应用内存缓存足够。Redis 层可在 QPS > 100 时引入。

#### ADR-C4: 初始数据填充

从当前 `location_trans.py` 提取现有 8 个城市，扩展为完整 Schema：

```sql
INSERT INTO cities (name_zh, name_en, name_aliases, iata_code, country)
VALUES
  ('北京', 'Beijing', '["北京市","Peking","PEK"]', 'PEK', 'CN'),
  ('上海', 'Shanghai', '["上海市","SHH"]', 'PVG', 'CN'),
  ('广州', 'Guangzhou', '["广州市"]', 'CAN', 'CN'),
  ('深圳', 'Shenzhen', '["深圳市"]', 'SZX', 'CN'),
  ('成都', 'Chengdu', '["成都市"]', 'CTU', 'CN'),
  ('杭州', 'Hangzhou', '["杭州市"]', 'HGH', 'CN'),
  ('巴塞尔', 'Basel', '["BASEL","BSL"]', 'BSL', 'CH'),
  ('苏黎世', 'Zurich', '["ZURICH","ZRH"]', 'ZRH', 'CH');
```

---

## 5. 子系统集成架构

### 5.1 完整请求-响应链路

```
┌─────────────────────────────────────────────────────────────────────┐
│                        单次对话请求全链路                              │
│                                                                      │
│  客户端                                                              │
│  POST /api/v1/graph/chat                                            │
│  Authorization: Bearer <JWT>                                        │
│  Body: {"user_input": "帮我查去苏黎世的航班"}                         │
│                                                                      │
│  ═══════════════ FASTAPI LAYER ═══════════════                      │
│                                                                      │
│  ┌─ Middleware Stack ────────────────────────────────────────────┐  │
│  │ 1. RequestIDMiddleware    → X-Request-ID: uuid                │  │
│  │ 2. CORSMiddleware         → 来源检查                           │  │
│  │ 3. RateLimitMiddleware    → 100/min 全局限流                   │  │
│  │ 4. AuthMiddleware         → JWT 解码 → user_id=1              │  │
│  │ 5. LoggingMiddleware      → 请求日志 (JSON 格式)               │  │
│  └──────────────────────────────────────────────────────────────┘  │
│                                                                      │
│  ┌─ graph_views.py ──────────────────────────────────────────────┐  │
│  │ 1. 解析 request.state.username → user_id, username            │  │
│  │ 2. 查 user_passenger_mapping → passenger_id                   │  │
│  │ 3. 构建 UserContext(user_id, username, passenger_id)          │  │
│  │ 4. 构建 thread_id = "user_1:{uuid}"                           │  │
│  └──────────────────────────────────────────────────────────────┘  │
│                                                                      │
│  ═══════════════ LANGGRAPH LAYER ═══════════════                    │
│                                                                      │
│  graph.stream(input, config, context=UserContext(...))               │
│                                                                      │
│  ┌─ Node: load_user_memory ──────────────────────────────────────┐  │
│  │  Runtime[UserContext] → user_id                               │  │
│  │  PostgresStore.get((users, 1), "preferences")                 │  │
│  │    → {"seat": "window", "hotel_star": 4}                      │  │
│  │  注入到 State.user_info                                       │  │
│  └──────────────────────────────────────────────────────────────┘  │
│                                                                      │
│  ┌─ Node: summarize ─────────────────────────────────────────────┐  │
│  │  检查 messages token 数                                       │  │
│  │    < 2048 → 跳过                                              │  │
│  │    >= 2048 → SummarizationNode 压缩                           │  │
│  └──────────────────────────────────────────────────────────────┘  │
│                                                                      │
│  ┌─ Node: primary_assistant ─────────────────────────────────────┐  │
│  │  Prompt: 系统指令 + user_info + 当前时间 + messages            │  │
│  │  LLM 决策:                                                    │  │
│  │    用户想查航班 → ToFlightBookingAssistant                   │  │
│  │    需要查政策 → lookup_policy tool                            │  │
│  └──────────────────────────────────────────────────────────────┘  │
│                                                                      │
│  ┌─ (可选) Tool: lookup_policy ──────────────────────────────────┐  │
│  │  Qdrant.search("退票政策", k=5)                               │  │
│  │  → 返回 top-5 FAQ 分块 + metadata                             │  │
│  └──────────────────────────────────────────────────────────────┘  │
│                                                                      │
│  ┌─ Sub-Agent: flight_agent ─────────────────────────────────────┐  │
│  │  Runtime[UserContext] → passenger_id                          │  │
│  │  调用工具: search_flights(departure="Shanghai", ...)           │  │
│  │    → ToolRuntime[UserContext] 自动注入                         │  │
│  │    → SQL: WHERE ... (数据按 passenger_id 过滤)               │  │
│  └──────────────────────────────────────────────────────────────┘  │
│                                                                      │
│  ┌─ Human-in-the-loop ───────────────────────────────────────────┐  │
│  │  interrupt_before: update_flight_sensitive_tools              │  │
│  │  PostgresSaver 保存当前状态                                    │  │
│  │  返回: "AI助手即将执行改签操作，是否确认？(输入'y'继续)"          │  │
│  └──────────────────────────────────────────────────────────────┘  │
│                                                                      │
│  ┌─ (用户确认后) Node: extract_memories ─────────────────────────┐  │
│  │  对话结束 → LLM 提取偏好                                       │  │
│  │  PostgresStore.put((users, 1), "preferences", {...})           │  │
│  │  审计日志: INSERT INTO audit_events (...)                     │  │
│  └──────────────────────────────────────────────────────────────┘  │
│                                                                      │
└─────────────────────────────────────────────────────────────────────┘
```

### 5.2 子系统依赖关系

```
app/graph/graph.py (图构建)
  ├── 依赖 app/db/engine.py (PostgreSQL 连接池, 用于 Checkpoint + Store)
  ├── 依赖 app/db/engine_mysql.py (MySQL, 用于业务数据查询)
  ├── 依赖 app/graph/state.py (State + UserContext 定义)
  ├── 依赖 app/graph/agents/ (各 Agent Prompt + Runnable)
  │     └── 依赖 app/graph/llm/ (LLM Provider)
  ├── 依赖 app/graph/tools/ (Tool 定义)
  │     ├── flights.py → app/db/repositories/flight.py (MySQL)
  │     ├── hotels.py → app/db/repositories/hotel.py
  │     ├── policy.py → Qdrant (HTTP)
  │     └── city_mapper.py → app/db/repositories/city.py (MySQL)
  └── 依赖 app/services/graph_service.py (编排 + 生命周期)

基础设施:
  MySQL (业务数据: flights, hotels, car_rentals, users, cities, audit_events)
  PostgreSQL (LangGraph 专用: checkpoint + store)
  Qdrant (向量存储: FAQ 分块)
  Redis (速率限制, JWT 黑名单)
  Cloud LLM API (OpenAI / DeepSeek)
```

### 5.3 Docker Compose 拓扑

```
services:
  app:        FastAPI (8000)
  mysql:      MySQL 8.0 (3306) - 业务数据
  postgres:   PostgreSQL 16 (5432) - Checkpoint + Store
  redis:      Redis 7 (6379) - 缓存 + 限流 + JWT 黑名单
  qdrant:     Qdrant (6333) - 向量存储
  nginx:      Nginx (80/443) - 反向代理
```

### 5.4 数据存储职责矩阵

| 存储 | 数据内容 | 生命周期 | 备份策略 |
|------|----------|----------|----------|
| MySQL | 用户账户、业务数据(航班/酒店/租车)、城市映射、审计日志 | 持久 | 每日全量 + binlog |
| PostgreSQL | LangGraph checkpoint、长期记忆(Store) | 30 天 checkpoint，持久 Store | checkpoint 不备份，Store 每日备份 |
| Qdrant | FAQ 向量嵌入 + 元数据 | 与源文档同步 | 重建成本低，仅备份分块元数据 |
| Redis | 速率限制计数器、JWT 黑名单 | 实时，可丢失 | 不备份 |

---

## 附录: 依赖变更清单

### 新增依赖

| 包 | 用途 | 阶段 |
|----|------|------|
| `langgraph-checkpoint-postgres` | PostgresSaver 检查点持久化 | Phase 2 |
| `psycopg[binary,pool]` | PostgreSQL 异步驱动 | Phase 2 |
| `langmem` | SummarizationNode 对话摘要 | Phase 2 |
| `langchain-qdrant` | Qdrant 向量存储集成 | Phase 2 |
| `qdrant-client` | Qdrant Python 客户端 | Phase 2 |
| `slowapi` | 速率限制中间件 | Phase 4 |
| `aiomysql` | MySQL 异步驱动 | Phase 2 |

### 移除依赖

| 包 | 原因 |
|----|------|
| `gradio` | 生产环境不需要 Gradio UI |
| `langchain-community` (Tavily) | Tavily 搜索工具移除 |
| `dynaconf` | 替换为 pydantic-settings |
| `loguru` | 统一到标准 logging (JSON 格式) |
| `sqlite3` (直接使用) | 业务数据迁移至 MySQL |

---

> **文档状态**: 等待审核  
> **下一步**: 确认设计方案后进入 Phase 0 紧急修复
