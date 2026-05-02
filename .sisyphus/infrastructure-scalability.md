# 生产级基础设施与扩展性设计

> **版本**: v1.0  
> **日期**: 2026-04-28  
> **关联文档**: `upgrade-architecture.md` / `subsystem-redesign.md`  
> **适用场景**: 50TB 混合文档 / 数千用户 / 混合云部署  

---

## 目录

1. [文档处理管线](#1-文档处理管线)
2. [分布式检索架构](#2-分布式检索架构)
3. [异步任务处理系统](#3-异步任务处理系统)
4. [对象存储架构](#4-对象存储架构)
5. [高可用架构](#5-高可用架构)
6. [监控告警体系](#6-监控告警体系)
7. [多级缓存架构](#7-多级缓存架构)
8. [API 网关与流量管理](#8-api-网关与流量管理)
9. [数据库分片与归档](#9-数据库分片与归档)
10. [安全与密钥管理](#10-安全与密钥管理)

---

## 1. 文档处理管线

### 1.1 核心挑战

| 维度 | 挑战 | 影响 |
|------|------|------|
| 文档量 | 50TB 混合类型 | 无法单机解析，需分布式处理 |
| 类型混合 | PDF / Office / 数据库导出 / 实时流 | 需要多解析器路由 |
| 更新频率 | 静态 + 近实时混存 | 分块策略不能一刀切 |
| 语言 | 纯中文 | 需中文优化 OCR、分词、嵌入 |

### 1.2 两阶段文档解析路由

生产系统的核心设计原则：**先检测类型，再路由到最优解析器**。不同类型走不同路径，避免"一刀切"带来的性能浪费。

```
文档输入流 (MinIO / Kafka)
  │
  ├── 类型检测层 (magic bytes / 扩展名 / 内嵌文本探测)
  │
  ├── 原生数字 PDF ──────→ PyMuPDF4LLM (快速文本提取, 10-50x faster)
  ├── 扫描件/图片 PDF ───→ MinerU + PaddleOCR (中文优化 OCR)
  ├── Office 文档 ───────→ Marker / Unstructured.io
  ├── HTML/网页 ─────────→ 专用 HTML 清洗器
  ├── 结构化数据(CSV/JSON)→ Schema 感知序列化器
  └── 实时数据流 ────────→ 固定窗口分块器 (确定性)
```

**中文场景关键选型**:
- **PaddleOCR**: 中文 OCR 事实标准，CJK 字符集覆盖完整
- **MinerU**: 复杂中文 PDF（竖排、合并单元格）优于通用方案
- **jieba / HanLP**: 中文分词，BM25 稀疏检索的前置依赖

### 1.3 Parent-Child 分块策略（生产黄金标准）

核心思想：**索引小块用于精准检索，返回大块用于生成上下文**。

```
父块 (1024-2048 tokens) → 存储于 MinIO / PostgreSQL
  ├── 子块 1 (128-200 tokens) → 嵌入 → 向量索引
  ├── 子块 2 (128-200 tokens) → 嵌入 → 向量索引
  └── 子块 N ...

查询流程:
  用户查询 → 混合检索匹配子块 → 查询父块 ID → 从 KV 存储取父块 → 去重 → 返回 LLM
```

**设计要点**:
- 父块不需要嵌入——只有子块进入向量索引，大幅降低嵌入成本
- 父块存储在 MinIO 或 PostgreSQL 中，1-10ms KV 查询即可获取
- 必须按 `parent_id` 去重，避免同一父块的多个子块重复返回

### 1.4 分块策略选择矩阵

| 文档类型 | 分块策略 | 子块大小 | 父块大小 | 原因 |
|---------|---------|---------|---------|------|
| 政策/法规文件 | 语义分块 + 句子边界 | 200 tokens | 1024 tokens | 按语义边界，保留完整段落 |
| 实时数据流 | 固定滑动窗口 | 256 tokens | — | 确定性，增量更新一致 |
| 表格密集文档 | 结构感知分块 | 逐表/逐行 | 整表 | 表格不可切割 |
| 法律/合同 | 句子级 + 大父块 | 128 tokens | 2048 tokens | 高精度检索 + 完整上下文 |
| 历史归档(低频) | 语义分块 | 200 tokens | 1024 tokens | 非确定性可接受 |

**关键原则**: 高频更新文档必须使用确定性分块（固定/递归字符分块）。语义分块在增量更新时会产生不一致边界，仅适用于低频归档数据。

---

## 2. 分布式检索架构

### 2.1 存储引擎选型

对于 50TB（数十亿级向量），单实例方案全部出局：

| 方案 | 最大规模 | 并发 QPS | 分片策略 | 运维复杂度 | 决策 |
|------|---------|----------|----------|-----------|------|
| Milvus 分布式 | 1000 亿+ | 10,000+ | 自动哈希 | 高 (7+组件) | **选用** |
| Elasticsearch + 向量 | ~10 亿 | 5,000+ | 手动 | 中 | 10TB 级备选 |
| Qdrant | ~10 亿 | 5,000+ | 分片键 | 低 | ≤10TB |
| pgvector | ~1 亿 | 1,000+ | 无内置 | 低 | ≤1TB |

**选择 Milvus 分布式模式**: 存储计算分离架构，原生支持水平扩展，是 50TB 级别唯一经过验证的生产方案。

### 2.2 Milvus 集群拓扑

```
┌─────────────────────────────────────────────┐
│               Load Balancer                  │
├─────────────────────────────────────────────┤
│  Proxy (无状态, 可水平扩展, 3-5 节点)         │
├─────────────────────────────────────────────┤
│  ┌───────────┐  ┌───────────┐  ┌──────────┐ │
│  │ QueryNode  │  │ DataNode  │  │ IndexNode │ │
│  │ (内存密集)  │  │ (IO 密集)  │  │ (CPU 密集) │ │
│  │ 搜索/检索   │  │ 数据刷写   │  │ 索引构建   │ │
│  │ 8-16 节点   │  │ 3-6 节点   │  │ 2-4 节点   │ │
│  │ 128GB+ RAM │  │ 32-64GB   │  │ 64GB+ RAM │ │
│  └───────────┘  └───────────┘  └──────────┘ │
├─────────────────────────────────────────────┤
│  etcd (元数据)  │  Pulsar/Kafka (消息队列)     │
├─────────────────────────────────────────────┤
│  MinIO / S3 (对象存储 — 向量+索引持久化)       │
└─────────────────────────────────────────────┘
```

**各组件职责**:
- **Proxy**: 无状态路由层，接收查询并转发到 QueryNode
- **QueryNode**: 内存中维护 HNSW 图，执行向量搜索。**内存密集型**——50TB 场景建议每节点 128GB+ RAM
- **DataNode**: 处理数据摄入和持久化刷写，**IO 密集型**
- **IndexNode**: 后台构建索引，**CPU 密集型**——建议安排在业务低峰期
- **etcd**: 分布式元数据协调
- **Pulsar/Kafka**: 组件间异步消息

### 2.3 分片规划

| 参数 | 50TB 场景推荐值 | 设计理由 |
|------|----------------|---------|
| 分片数 | 4-8 | 1-2 分片/50-200M 实体。50TB 约 1-2 亿向量 |
| 索引类型 | IVF_SQ8 | 内存效率 vs 召回率的平衡点。HNSW 精度更高但内存开销大 |
| 度量 | Inner Product | 归一化后等价于余弦相似度 |
| nlist | 4096-16384 | 聚类中心数，越大召回越高但构建越慢 |
| nprobe | 64-256 | 查询时搜索的聚类数，动态调整平衡延迟和召回 |
| 副本数 | 3 | 容忍 2 节点故障 |

**关键约束**: `shard_num` 创建集合后**不可变更**。必须提前规划容量。

### 2.4 检索漏斗（多阶段渐进检索）

50TB 级语料库不能平面搜索——必须渐进缩小候选集：

```
阶段 1: 粗粒度过滤 (稀疏检索)
  将相关文档聚类为粗粒度单元 (~4K tokens)
  → 从亿级 → 万级候选 (减少 97%)

阶段 2: 中度过滤 (密集检索)
  粗粒度单元分割为文档级 (~1K tokens)
  → 从万级 → 千级候选

阶段 3: 精细排序 (交叉编码器)
  文档级分割为段落级 (~100 tokens)
  → 从千级 → 百级候选 → Top-5 返回
```

**混合检索并行模式**:

```
用户查询
  ├── 嵌入向量化 → Milvus HNSW 搜索 → Top-30 (向量分数)
  └── 分词(BM25) → 稀疏搜索 → Top-30 (BM25 分数)
          ↓
    Reciprocal Rank Fusion (RRF) 融合
          ↓
    合并 Top-20 → 交叉编码器重排序 → Top-5 最终上下文
```

**重排序选型**:
- 中文场景推荐: **BAAI BGE-Reranker-v2-m3** (自托管) 或 **Cohere Rerank 3.5** (API)
- 候选窗口 Top-20~25 已捕获大部分精度；扩展到 50 仅增加延迟
- 查询明确时（top-k 分差大）可跳过重排序，节省 30-80ms

---

## 3. 异步任务处理系统

### 3.1 设计原则

核心哲学: **同步（面向用户）和异步（处理）工作负载分离**。

- FastAPI 处理用户请求（同步，低延迟）
- Celery/Kafka Worker 处理文档解析、分块、嵌入（异步，高吞吐）
- 两条链路通过 Redis/Kafka 消息队列解耦

### 3.2 分层队列设计

50TB 混合文档需要**多优先级、多类型的队列**：

| 队列 | 优先级 | 处理内容 | Worker 配置 | 扩缩策略 |
|------|--------|----------|-----------|---------|
| `urgent_reindex` | 最高 | 实时数据流更新 | 轻量嵌入 Worker | 即时响应 |
| `pdf_deep_parse` | 高 | PDF 解析 + OCR | GPU Worker (PaddleOCR) | 按队列深度 |
| `office_parse` | 中 | Office 文档转换 | CPU Worker | 定时伸缩 |
| `batch_ingest` | 低 | 批量导入、全量重建 | 混合 GPU/CPU | 夜间最大 |
| `retry_dlq` | 最低 | 失败文档重试 | — | 人工触发 |

### 3.3 Celery + Redis 架构

```
┌──────────┐    ┌──────────────┐    ┌──────────────────────────┐
│ FastAPI  │───→│ Redis (Broker)│───→│  Celery Worker Pool      │
│ (同步层)  │    │              │    │  ├─ ParseWorker × 5     │
└──────────┘    └──────────────┘    │  ├─ OCRWorker × 3       │
                                    │  ├─ ChunkWorker × 10    │
                                    │  └─ EmbedWorker × 5     │
                                    └──────────┬───────────────┘
                                               │
                                    ┌──────────▼───────────────┐
                                    │  Milvus (向量写入)         │
                                    │  MinIO (解析结果存储)      │
                                    │  PostgreSQL (任务状态)     │
                                    └──────────────────────────┘
```

**关键设计**:
- API 立即返回 `202 Accepted`，创建 Pending 记录
- Worker 处理完成后更新任务状态
- 客户端轮询或 Webhook 获取处理结果
- 任务状态持久化在 PostgreSQL，Worker 宕机可恢复

### 3.4 Kafka 升级路径（吞吐量再大一个量级时）

当 Celery 吞吐量不足时，升级到 Kafka + 微服务:

```
Kafka Topics:
  raw-documents → 解析微服务 → parsed-documents
                                 ↓
                           分块微服务 → chunks
                                 ↓
                           嵌入微服务 → vectors
                                 ↓
                           索引写入服务 → Milvus + MinIO

优势:
  - 消息永久保留（可回放重试）
  - 微服务独立扩缩
  - 天然死信队列
  - 幂等处理保证
```

**变更数据捕获 (CDC) 模式**: 对数据库中的结构化数据，使用 Debezium → Kafka → Flink 流处理 → 增量向量更新。

---

## 4. 对象存储架构

### 4.1 MinIO 分布式部署

50TB 场景需 MinIO **分布式模式 + 纠删码**:

| 组件 | 要求 |
|------|------|
| 节点数 | 最低 4 节点，推荐 8-16 节点 |
| 每节点存储 | 8+ NVMe SSD |
| 每节点内存 | 128GB+ |
| 每节点 CPU | 16+ vCPU，支持 AVX-512 |
| 网络 | 100GbE |
| 纠删码 | 8+2 或 6+2（容忍 2 节点故障） |

### 4.2 桶结构与生命周期

```
minio-cluster/
  ├── documents/                    # 原始文档存储
  │   ├── raw/                      # 上传原件 (PDF/DOCX/XLSX)
  │   │   └── 30 天后转 WARM 层
  │   ├── parsed/                   # 解析后结构化内容 (JSON/Markdown)
  │   └── images/                   # 提取的图片/图表
  ├── vectors/                      # 向量索引快照
  │   └── 365 天后过期删除
  ├── models/                       # 嵌入模型仓库
  ├── temp/                         # 临时上传区
  │   └── 7 天后过期删除
  └── backups/                      # 系统备份
      └── 90 天后过期删除
```

**存储分层策略**:

| 层级 | 介质 | 适用数据 | 延迟 |
|------|------|---------|------|
| HOT | NVMe SSD | 近 30 天文档、最近查询缓存 | < 1ms |
| WARM | SATA SSD | 30-90 天文档、历史向量索引 | < 5ms |
| COLD | HDD / 云端 | 90 天+ 归档文档、旧版本文档 | < 50ms |

---

## 5. 高可用架构

### 5.1 PostgreSQL HA: Patroni + HAProxy + PgBouncer

```
App Pods → PgBouncer (连接池) → HAProxy → Patroni PG 集群 (1 主 + 2 从)
```

**PgBouncer 连接池**（生产必备）:
- `pool_mode = transaction`: 一个物理连接服务数十个并发请求
- LLM 调用期间仅在实际查询时占用连接（毫秒级），释放后供其他请求复用
- 部署 2+ PgBouncer 实例避免单点故障

**故障转移流程**:
1. Patroni 通过 etcd 检测主库故障
2. 自动提升从库为新主（5-30 秒）
3. HAProxy 健康检查感知变更，重定向流量
4. PgBouncer 断连自动重连

### 5.2 MySQL HA: ProxySQL + Orchestrator

```
App Pods → ProxySQL → MySQL 集群 (1 主 + N 从)
                        ├── 写: hostgroup 10 (主)
                        └── 读: hostgroup 20 (从)
```

**读写分离**: SELECT 自动路由到从库，SELECT FOR UPDATE / INSERT / UPDATE 路由到主库。

**从库滞后保护**: ProxySQL 自动排除滞后超过 30s 的从库。

### 5.3 Redis HA: Sentinel 集群

- 1 主 + 2+ 从 + 3+ Sentinel 进程（奇数，跨可用区部署）
- Quorum 公式: floor(N/2) + 1。3 Sentinel → quorum=2，容忍 1 故障
- 裂脑防护: `min-replicas-to-write 2` + `min-replicas-max-lag 10`

### 5.4 整体 HA 拓扑

```
                         ┌──────────────┐
                         │   Kong/APISIX │ (2+ 实例, 负载均衡)
                         └──────┬───────┘
                                │
                ┌───────────────▼────────────────┐
                │     FastAPI (K8s Deployment)     │
                │     HPA: min=3, max=20           │
                │     PodDisruptionBudget: min=2   │
                └────┬──────┬──────┬──────────────┘
                     │      │      │
        ┌────────────▼──┐ ┌─▼──────────┐ ┌───────▼──────────┐
        │ PostgreSQL HA  │ │  MySQL HA  │ │  Redis Sentinel  │
        │ Patroni+       │ │ ProxySQL+  │ │  1主+2从+3哨兵   │
        │ PgBouncer+     │ │Orchestrator│ │                  │
        │ HAProxy        │ │            │ │                  │
        └───────────────┘ └────────────┘ └──────────────────┘

        ┌────────────────┐ ┌────────────────────┐
        │ Milvus 集群     │ │  MinIO 集群         │
        │ 3+ 副本         │ │  8+ 节点, 纠删码    │
        └────────────────┘ └────────────────────┘
```

---

## 6. 监控告警体系

### 6.1 可观测性栈

```
应用层: FastAPI + LangGraph
  │
  ├── Metrics → Prometheus → Grafana (仪表盘 + 告警)
  ├── Logs    → Loki → Grafana (日志查询)
  └── Traces  → Tempo/Jaeger → Grafana (分布式追踪)
```

### 6.2 RAG 系统核心指标

**RED 方法 (Rate / Errors / Duration)**:

| 指标 | 含义 | 告警阈值 |
|------|------|---------|
| 请求速率 | QPS 趋势 | 突降 > 50% 告警 |
| 错误率 | 5xx / 总请求 | > 5% (2min) → Critical |
| P99 延迟 | 端到端响应时间 | > 5s (2min) → Warning |

**LLM 专用指标**:

| 指标 | 说明 |
|------|------|
| `llm_tokens_in/out_total` | Token 消耗统计，用于成本核算 |
| `llm_errors_total` | LLM API 调用失败次数 |
| `external_api_latency_seconds` | LLM / 向量数据库 外部 API 延迟分布 |
| `rag_vector_search_duration_seconds` | 向量检索延迟 |
| `rag_cache_hit_ratio` | 缓存命中率 |
| `rag_retrieved_chunks_count` | 每次查询返回的分块数 |

### 6.3 告警规则

| 告警 | 条件 | 严重度 |
|------|------|--------|
| 后端宕机 | `up{job="fastapi"} == 0` (1min) | Critical |
| 高错误率 | 5xx 占比 > 5% (2min) | Critical |
| LLM 错误激增 | `rate(llm_errors[5m]) > 0.1` | Critical |
| P99 延迟恶化 | `p99 > 5s` (2min) | Warning |
| Token 成本异常 | 输出 token > 1M/min | Warning |
| 向量搜索变慢 | `p95 > 1s` (5min) | Warning |
| 缓存命中率下降 | 命中率 < 30% (10min) | Warning |

### 6.4 分布式追踪 (OpenTelemetry)

LangGraph 多智能体系统的追踪需要覆盖三个维度：

| Span 类型 | 覆盖内容 |
|-----------|---------|
| `invoke_agent` | 图/子 Agent 完整执行 |
| `execute_tool` | 单个工具调用 (参数 + 结果) |
| `langgraph.node` | 图节点执行 (状态变更 + 路由决策) |

**用户上下文传播**: 所有 Span 自动携带 `user_id`、`conversation_id`，支持按用户/会话维度查询。

---

## 7. 多级缓存架构

### 7.1 四级缓存模型

```
用户查询
  │
  ▼
L1: 精确匹配缓存 (应用内存 + Redis)      ~1ms
  命中条件: SHA256(query + top_k + model) 完全相同
  TTL: 1 小时
  │
  ▼
L2: 语义缓存 (Redis Vector Search)       ~50ms
  命中条件: cosine_similarity > 0.92
  TTL: 1 小时
  │
  ▼
L3: 检索缓存 (Redis)                    ~100ms
  命中条件: 相同 embedding → 相同 top-k 分块 ID
  TTL: 7 天 (文档变更时失效)
  │
  ▼
L4: 全量管线 (Embedding → VectorDB → LLM)  ~2-8s
  全部未命中时执行
```

### 7.2 缓存失效策略

| 策略 | 机制 | 适用场景 |
|------|------|---------|
| **命名空间版本化** (推荐) | 所有 key 带版本前缀 `v{N}`。模型/文档变更时递增版本号，旧 key TTL 自然过期 | Prompt 变更、模型升级 |
| **文档驱动失效** | 源文档更新时，删除引用该文档 ID 的缓存条目 | 文档刷新管线 |
| **TTL 时间过期** | 固定过期时间 | 默认策略 |

**成本节省预估**: 生产系统报告多级缓存可降低 60-68% 的 LLM 调用成本。

---

## 8. API 网关与流量管理

### 8.1 网关选型

| 特性 | Kong | APISIX | 推荐 |
|------|------|--------|------|
| AI 代理功能 | 企业版 | **开源** (ai-proxy 插件) | APISIX |
| Token 级限流 | 企业版 | **开源** | APISIX |
| 多模型路由 | 企业版 | **开源** | APISIX |
| 性能 | ~15K req/s/core | ~20K req/s/core | APISIX |
| 插件语言 | Lua | Lua/Go/Python/Wasm | APISIX |

**选择 APISIX**: 开源 AI 功能（多模型路由、token 级限流、prompt 转换）不需要企业授权。

### 8.2 认证链路

```
客户端 → API Gateway (TLS 终止)
          ↓
    Auth Plugin (JWT / OAuth2 / API Key 验证)
          ↓
    Rate Limiting (消费者级 + 路由级)
          ↓
    Request Transform (Header 注入, CORS)
          ↓
    Upstream → FastAPI Service (集群内)
```

### 8.3 多级限流

| 级别 | 策略 | 适用对象 |
|------|------|---------|
| 全局 | 1000 req/min | 所有用户 |
| 消费者 | Free: 10/min / Premium: 100/min | 按用户等级 |
| Token | 100K tokens/min (通过 LLM API 代理) | LLM 成本控制 |
| 工具 | 5/min (登录/注册等敏感端点) | 防暴力破解 |

---

## 9. 数据库分片与归档

### 9.1 时间范围分区（核心策略）

对于审计日志、对话 checkpoint 等高写入表，使用**按月 RANGE 分区**：

```
单表 (未分区) vs 月分区
  点查询 (按时间):  12.4ms → 1.8ms   (6.9× faster)
  范围扫描 (1 天):   8.7s  → 0.32s  (27.2× faster)
  删除 1 月数据:    47min → 0.003s  (DROP PARTITION, 约 100 万倍)
  VACUUM:           2.1h  → 8.2min  (15× faster)
```

### 9.2 自动化分区管理

使用 `pg_partman` 扩展自动创建和维护分区:
- 自动预创建未来 3 个月的分区
- 自动归档超过保留期的分区（6 个月后 detach → 压缩 → 导出 MinIO）
- 保留策略: `retention = 6 months`

### 9.3 数据生命周期

```
HOT  (0-30 天)   → 分区表, SSD 存储, 在线查询
WARM (30-90 天)  → 分区表, 标准存储
COLD (90 天-2 年) → detach → 压缩 → MinIO 归档
PURGE (>2 年)    → 删除 (合规要求除外)
```

### 9.4 高写入缓冲模式

若写入速率 > 50K/s（审计日志），引入 Kafka 缓冲层:

```
App → Kafka (缓冲) → Stream Processor → DB 批量写入 (每 5s 或 10K 条)
```

将随机写入转换为高效的顺序批量插入。

---

## 10. 安全与密钥管理

### 10.1 HashiCorp Vault 架构

```
                 ┌──────────────────┐
                 │  Cloud KMS       │ ← Auto-unseal 密钥
                 │  (AWS/GCP/Azure) │
                 └────────┬─────────┘
                          │ 加密 barrier
                 ┌────────▼─────────┐
                 │  Vault HA 集群    │
                 │  (3+ 节点, Raft) │
                 └────────┬─────────┘
                          │
    ┌─────────────────────┼─────────────────────┐
    │                     │                     │
 App (SDK)        Vault Agent         Dynamic Secrets
 短期 token         (Sidecar)          (自动轮换凭证)
                   渲染 .env 文件
```

### 10.2 动态密钥（数据库凭证）

**不使用静态数据库密码**。Vault 动态密钥引擎自动生成短期凭证：

- 每次 App 连接时向 Vault 请求新的数据库凭证
- TTL: 1 小时，自动过期
- 最大 TTL: 24 小时
- 连接关闭时自动撤销

### 10.3 密钥轮换策略

| 密钥类型 | 轮换周期 | 方法 |
|---------|---------|------|
| LLM API 密钥 | 30-90 天 | Vault KV v2 版本化 |
| 数据库凭证 | **1 小时** | 动态密钥 (自动) |
| JWT 签名密钥 | 30 天 | Vault Transit 引擎 |
| 云服务凭证 | 12 小时 | STS / Workload Identity |
| Redis 密码 | 30 天 | Vault KV + App 重启 |

### 10.4 蓝绿轮换（零停机静态密钥轮换）

```
/secrets/apikeys/blue/llm-openai   (当前活跃)
/secrets/apikeys/green/llm-openai  (新密钥)

流程:
  1. 轮换 green 路径为新密钥
  2. 部署 50% Pod 使用 green 路径
  3. 验证通过
  4. 迁移剩余 50%
  5. 轮换 blue（现为备份）
```

---

## 附录: 依赖矩阵

### 新增基础设施组件

| 组件 | 用途 | 部署模式 |
|------|------|---------|
| Milvus (分布式) | 50TB 向量存储与检索 | K8s / Docker Compose |
| MinIO (分布式) | 50TB 原始文档对象存储 | 8-16 节点集群 |
| Celery + Redis | 异步文档处理任务队列 | K8s Worker Pool |
| Patroni + etcd | PostgreSQL 高可用 | 3 节点集群 |
| PgBouncer | PostgreSQL 连接池 | 2+ 实例 |
| ProxySQL | MySQL 读写分离 + 连接池 | 2+ 实例 |
| Prometheus + Grafana | 监控 + 告警 | 单实例 (可扩展) |
| OpenTelemetry Collector | 分布式追踪 | DaemonSet |
| APISIX | API 网关 | 2+ 实例 |
| HashiCorp Vault | 密钥管理 | 3+ 节点 HA |
| Kafka (预留) | 高吞吐消息队列 | 3+ Broker |

### 文档体系

| 文档 | 覆盖内容 |
|------|---------|
| `upgrade-architecture.md` | 全局架构升级 (项目结构、配置、数据层、API、Agent、测试、部署) |
| `subsystem-redesign.md` | 核心子系统重设计 (RAG、记忆机制、用户身份、城市映射) |
| `infrastructure-scalability.md` (本文档) | 基础设施与扩展性 (文档管线、分布式检索、HA、监控、缓存、网关、安全) |

---

> **三份文档完整覆盖**: 应用架构 → 核心子系统 → 基础设施与扩展性
