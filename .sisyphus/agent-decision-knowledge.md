# Agent 决策智能与知识生命周期设计

> **版本**: v1.0  
> **日期**: 2026-04-28  
> **关联文档**: `upgrade-architecture.md` / `subsystem-redesign.md` / `infrastructure-scalability.md` / `agent-governance-layered.md`  
> **定位**: Agent 架构师最终审视 —— 决策可解释性 + 知识全生命周期  

---

## 目录

1. [决策溯源](#1-决策溯源)
2. [置信度估计](#2-置信度估计)
3. [确定性重放](#3-确定性重放)
4. [知识生命周期管理](#4-知识生命周期管理)
5. [Agent 协作模式扩展](#5-agent-协作模式扩展)
6. [用户体验度量](#6-用户体验度量)
7. [Agent 自检机制](#7-agent-自检机制)
8. [与前序文档的集成](#8-与前序文档的集成)

---

## 1. 决策溯源

### 1.1 核心问题

当前系统只能看到 Agent 的**最终行为**（调了什么工具、输出了什么文本），看不到**决策过程**（为什么选这个工具？考虑过哪些备选？当时有多确定？）。

生产级 Agent 系统需要**完整的决策链记录**，确保：
- 用户投诉时可以回溯根因
- Prompt 优化时可以对比决策质量
- 合规审计时可以追溯每一个自动化决策

### 1.2 决策链数据结构

```
DecisionNode {
  node_id: str                    # 图节点名称
  timestamp: UTC ISO 8601
  
  # 执行上下文
  prompt_version: str             # PromptHub commit hash
  model_name: str                 # 使用的 LLM 模型
  model_temperature: float
  input_tokens: int
  output_tokens: int
  
  # 决策细节
  decision_type: "routing" | "tool_selection" | "answer_generation"
  
  candidates: [                   # 备选方案 (仅路由和工具选择)
    { option: str, score: float, reasoning: str }
  ]
  
  selected: str                   # 选中的方案
  
  # 检索上下文 (仅回答生成)
  retrieved_docs: [               # 使用的检索文档
    { doc_id: str, chunk_id: str, similarity: float }
  ]
  
  # 置信度
  confidence: float               # 0.0 - 1.0
  
  # 结果
  status: "success" | "error" | "clarification_needed"
  latency_ms: int

  # 用户交互
  user_confirmed: bool | null     # 人机交互确认结果
}
```

### 1.3 决策树可视化

每条对话最终可渲染为决策树：

```
User: "帮我改签下周三北京到苏黎世的航班"

├─ [primary_assistant]
│   ├─ candidates:
│   │   ├─ ToFlightBookingAssistant (0.92) ← 选中
│   │   ├─ search_flights (0.45)
│   │   └─ lookup_policy (0.12)
│   ├─ decision: "用户明确查询航班，委托给航班助手"
│   ├─ confidence: 0.92
│   └─ latency: 1.2s
│
├─ [flight_agent]
│   ├─ decision_type: tool_selection
│   ├─ candidates:
│   │   ├─ search_flights (0.94) ← 选中
│   │   └─ fetch_user_flight_information (0.78)
│   ├─ decision: "先搜索可用航班，再查看用户现有机票"
│   ├─ confidence: 0.94
│   └─ latency: 0.8s
│
├─ [search_flights tool]
│   ├─ params: {departure: "北京", arrival: "苏黎世", date: "2026-04-30"}
│   ├─ results: 12 flights
│   └─ latency: 0.3s
│
├─ [flight_agent]
│   ├─ decision_type: tool_selection
│   ├─ candidates:
│   │   ├─ update_ticket_to_new_flight (0.88) ← 选中
│   │   └─ search_flights (0.65)
│   ├─ decision: "用户已有机票，直接改签"
│   ├─ confidence: 0.88
│   └─ latency: 0.9s
│
├─ [INTERRUPT: flight_sensitive_tools]
│   ├─ action: update_ticket_to_new_flight(ticket="1234567890", flight=789)
│   ├─ user_confirmed: ✓
│   └─ latency: (等待用户响应)
│
└─ [flight_agent final]
    ├─ decision_type: answer_generation
    ├─ retrieved_docs: 3 docs
    ├─ confidence: 0.95
    ├─ status: success
    └─ total_latency: 8.2s
```

### 1.4 存储方案

决策链存储在**专用的 `decision_traces` 表**（MySQL 分区表），与 LangSmith 追踪互补：

```
decision_traces 表:
  - trace_id: UUID (关联 LangSmith trace)
  - thread_id: str
  - user_id: int
  - decision_path: JSON (完整决策链)
  - prompt_versions: JSON (各节点使用的 Prompt 版本)
  - total_tokens: int
  - total_cost: decimal
  - user_feedback: "positive" | "negative" | null
  - created_at: timestamp

决策链作为 JSON 存储，支持:
  - 按用户/时间/Agent 查询
  - 用户投诉时直接检索对应决策链
  - 统计分析: "哪些决策路径最常出错？"
```

### 1.5 集成到分层架构

决策溯源是 **L6 治理层**的横切关注点。每个图节点执行前后由中间件自动记录，Agent 开发者无需手动埋点：

```
编排层节点执行
  │
  ├── [before hook] 记录节点开始时间、Prompt 版本
  ├── Agent 层执行
  ├── [after hook] 收集候选方案、置信度、选中的方案
  └── 写入 DecisionNode → 追加到 decision_path
```

---

## 2. 置信度估计

### 2.1 为什么需要置信度

Agent 不是万能的。以下场景必须有置信度：

| 场景 | 无置信度的后果 | 有置信度的处理 |
|------|--------------|--------------|
| 路由不确定 | 路由到错误子 Agent，浪费时间 | 低置信度 → 请求用户澄清: "您是想要改签航班还是取消航班？" |
| 检索质量差 | 用不相关内容回答，产生幻觉 | 低置信度 → 告知用户: "我找到的信息可能不够准确..." |
| 工具选择模糊 | 选了次优工具 | 低置信度 → 展示多个选项给用户选择 |
| 回答不确定 | 用户基于错误信息做决策 | 低置信度 → 标注: "以下信息仅供参考，建议核实" |

### 2.2 四类置信度

```
1. 路由置信度 (Routing Confidence)
   - 含义: Agent 有多大把握应该路由到某个子 Agent 或调用某个工具
   - 来源: LLM 输出的 tool_call 可以附带 logprobs
   - 阈值: < 0.7 → 请求用户澄清

2. 检索置信度 (Retrieval Confidence)
   - 含义: 检索到的文档与用户问题的相关程度
   - 来源: Milvus 返回的 similarity score 分布
   - 判断: top-1 score < 0.6 或 top-3 scores 差异 < 0.1 → 低置信度

3. 事实置信度 (Factuality Confidence)
   - 含义: 生成回答中每个声明是否被检索文档支撑
   - 来源: 幻觉检测层 (NLI 模型逐声明验证)
   - 阈值: 任意声明得分 < 0.5 → 标记为低置信度

4. 回答置信度 (Answer Confidence)
   - 含义: Agent 对整体回答正确性的综合判断
   - 来源: 上述三项的加权综合
   - 展示: UI 显示置信度指示器 (绿/黄/红)
```

### 2.3 置信度计算模型

```
Answer Confidence = 
  路由置信度 × 0.2 +
  检索置信度 × 0.3 +
  事实置信度 × 0.5

加权理由:
  - 事实置信度权重最高 (50%): 回答是否正确取决于事实是否被支撑
  - 检索置信度次之 (30%): 检索质量直接影响生成质量
  - 路由置信度最低 (20%): 路由错不一定回答错
```

### 2.4 低置信度处理矩阵

| 置信度区间 | UI 展示 | Agent 行为 | 记录 |
|-----------|---------|-----------|------|
| 0.85 - 1.00 | 无特殊标记 | 正常响应 | 无 |
| 0.70 - 0.85 | 黄灯 ⚠️ "仅供参考" | 正常响应 + 提示 | 记录到评估数据集 |
| 0.50 - 0.70 | 橙灯 🔶 "准确性较低" | 提供多个选项 | 标记人工审核 |
| < 0.50 | 红灯 🔴 "无法确认" | 拒绝回答，建议转人工 | 自动创建改进任务 |

---

## 3. 确定性重放

### 3.1 设计目标

当生产环境出现问题时，必须能够**完全复现**当时的对话状态，找到根因。

普通 Debug 的问题: "再跑一次看会不会出错" —— 但 LLM 有随机性，相同的输入可能产生不同的输出。无法保证复现。

确定性重放的保证: **使用当时的精确状态重跑，保证输出一致**。

### 3.2 重放的三层冻结

```
Layer 1: 状态冻结
  - 从 PostgresSaver 加载当时 thread 的 checkpoint
  - 获得当时的完整 State (messages, dialog_state, user_info)

Layer 2: 配置冻结
  - Prompt 版本: 锁定到当时的 commit hash
  - Model 版本: 记录当时的模型名称和 temperature
  - LLM 响应: 录制当时 LLM 的原始响应 (tool_calls + content)
  - 检索结果: 录制当时 Qdrant/Milvus 返回的文档 ID 列表

Layer 3: 外部依赖 Mock
  - LLM API → 用录制的响应替代 (不发起真实 API 调用)
  - Vector DB → 用录制的检索结果替代
  - MySQL/PostgreSQL → 使用当时的事务快照或备份
```

### 3.3 录制机制

每次生产调用自动录制:

```python
class DeterministicRecorder:
    """在每次图执行时录制所有外部依赖的输入输出"""

    def __init__(self):
        self.recordings = []

    def record_llm_call(self, prompt_hash: str, input_messages: list, output: dict):
        self.recordings.append({
            "type": "llm_call",
            "prompt_hash": prompt_hash,
            "model": settings.LLM_MODEL,
            "input": input_messages,
            "output": output,  # 包括 tool_calls 和 content
        })

    def record_vector_search(self, query_hash: str, embedding: list, results: list):
        self.recordings.append({
            "type": "vector_search",
            "query_hash": query_hash,
            "results": [r["chunk_id"] for r in results],
        })

    def save(self, thread_id: str):
        """保存录制到 MinIO 冷存储，保留 30 天"""
        key = f"replay/{thread_id}/{datetime.utcnow().isoformat()}.json"
        minio_client.put_object(key, json.dumps(self.recordings))
```

### 3.4 重放执行

```python
class DeterministicReplayer:
    """使用录制的响应重放图执行"""

    def __init__(self, thread_id: str, recording_id: str):
        self.recordings = load_from_minio(thread_id, recording_id)
        self.recording_idx = 0

    def mock_llm(self, prompt_hash: str, input_messages: list) -> dict:
        recording = self.recordings[self.recording_idx]
        assert recording["type"] == "llm_call"
        assert recording["prompt_hash"] == prompt_hash
        self.recording_idx += 1
        return recording["output"]

    def replay(self, graph, checkpoint):
        """用 mock 的依赖重放完整图执行"""
        with mock.patch("app.infrastructure.llm.openai.ChatOpenAI.invoke", self.mock_llm):
            events = graph.stream(None, checkpoint.config, stream_mode="values")
            for event in events:
                print(f"Node: {event.get('node_name')}, State: {event}")
```

### 3.5 录制存储策略

| 维度 | 策略 |
|------|------|
| 存储位置 | MinIO 冷存储 |
| 保留时间 | 30 天 |
| 录制粒度 | 仅录制 LLM 调用和向量搜索（最不可预测的依赖） |
| 触发条件 | 仅当用户反馈 negative 或护栏触发时录制 |
| 采样率 | 线上 1% 随机采样用于质量分析 |

---

## 4. 知识生命周期管理

### 4.1 完整生命周期

当前 RAG 只覆盖了"摄入 → 检索"。生产级需要覆盖从**创建到废弃**的完整环：

```
┌──────────────────────────────────────────────────────────────┐
│                    知识生命周期闭环                           │
│                                                               │
│  ┌──────────┐                                                │
│  │ 1. 摄入  │  MinIO 文档上传 → 异步解析 → 分块              │
│  └────┬─────┘                                                │
│       ▼                                                      │
│  ┌──────────┐                                                │
│  │ 2. 验证  │  格式完整性 · 内容去重 · 权限检查 · 合规扫描   │
│  └────┬─────┘                                                │
│       ▼                                                      │
│  ┌──────────┐                                                │
│  │ 3. 冲突  │  新旧文档事实比对 · 矛盾标记 · 权威性排序      │
│  │   检测   │                                                │
│  └────┬─────┘                                                │
│       ▼                                                      │
│  ┌──────────┐                                                │
│  │ 4. 索引  │  分块 → 嵌入 → Milvus 写入 · 元数据写入 PG     │
│  └────┬─────┘                                                │
│       ▼                                                      │
│  ┌──────────┐                                                │
│  │ 5. 服务  │  lookup_policy tool · 检索 + 重排序            │
│  └────┬─────┘                                                │
│       │                                                       │
│  ┌────┴──────────────────────────────┐                       │
│  ▼                  ▼                ▼                       │
│ ┌──────┐    ┌──────────────┐  ┌──────────────┐              │
│ │高命中│    │   低命中      │  │   检索失败    │              │
│ │高质量│    │  人工审核队列  │  │  记录知识缺口 │              │
│ └──┬───┘    └──────┬───────┘  └──────┬───────┘              │
│    │               │                 │                        │
│    ▼               ▼                 ▼                        │
│ ┌──────────────────────────────────────────────┐             │
│ │            6. 知识反馈 (Feedback)              │             │
│ │                                               │             │
│ │  高频高质文档 → 提升检索权重 (boost_factor)    │             │
│ │  过时文档 (如旧版政策) → 标记 deprecated       │             │
│ │  矛盾文档 (新旧冲突) → 标记 conflict            │             │
│ │  缺失知识 → 自动生成补充任务单                  │             │
│ └──────────────────┬───────────────────────────┘             │
│                    ▼                                          │
│  ┌──────────┐                                                │
│  │ 7. 废弃  │  TTL 到期 · 人工标记 · 批量归档 · 索引删除     │
│  └──────────┘                                                │
│                                                               │
└──────────────────────────────────────────────────────────────┘
```

### 4.2 知识文档元数据模型

每个分块在向量存储中携带完整元数据：

```json
{
  "doc_id": "swiss-air-policy-2026-q1",
  "chunk_id": "swiss-air-policy-2026-q1-chunk-42",
  "title": "瑞士航空改签政策",
  "section": "如何更改预订",
  "source_file": "s3://documents/policies/swiss_air_change_policy_2026q1.pdf",
  "source_type": "official_policy",
  "source_authority": "high",
  "language": "zh-CN",
  "effective_date": "2026-01-01",
  "expiry_date": "2026-12-31",
  "ingested_at": "2026-01-15T10:30:00Z",
  "content_hash": "sha256:abc123...",
  "version": 1,
  "status": "active",
  "boost_factor": 1.0,
  "conflicts_with": [],
  "supersedes": [],
  "access_level": "public"
}
```

### 4.3 知识冲突管理

在 50TB 规模下，冲突不可避免。需要**冲突检测 + 解决策略**：

**检测机制**:
```
当新文档入库时:
  1. 计算新文档每个分块的 embedding
  2. 在 Milvus 中搜索 cosine similarity > 0.85 的已有分块
  3. 对高相似度分块对，用 LLM 逐条比对关键事实:
     "文档 A 声称: '经济舱改签费 ¥500'
      文档 B 声称: '经济舱改签费 ¥800'
      这两条信息是否矛盾？"
  4. 矛盾 → 标记 conflict
```

**解决策略**:
| 冲突类型 | 解决策略 | 示例 |
|---------|---------|------|
| 新旧政策 | 新文档覆盖（保留旧文档，权重降为 0.1） | 2026 年 Q2 政策替换 Q1 |
| 不同来源 | 权威性排序（官方的覆盖第三方） | 官网 PDF > 客服邮件 > 论坛帖子 |
| 同源矛盾 | 人工介入 | 同一文档中价格表与文字描述不一致 |
| 语言版本差异 | 以源语言为准 | 英文原文与中文翻译不一致 |

### 4.4 知识缺口自动发现

通过分析检索失败的对话，自动识别知识缺口：

```
知识缺口发现流程:
  1. 收集 lookup_policy 工具的调用记录
  2. 筛选低置信度或用户踩的对话
  3. 对未回答的问题进行聚类 (embedding → k-means)
  4. 对每个聚类，LLM 总结: "用户反复询问 X，但知识库中没有相关信息"
  5. 生成知识缺口工单:
     {
       "gap_id": "gap-2026-0428-001",
       "topic": "瑞士航空宠物运输政策",
       "frequency": 47,  # 过去 30 天被问 47 次
       "sample_queries": ["可以带猫上飞机吗？", "宠物托运怎么收费？"],
       "recommended_source": "swiss.com 宠物运输页面",
       "priority": "high",
       "created_at": "2026-04-28"
     }
  6. 推送到文档团队的任务队列
```

### 4.5 知识废弃策略

| 条件 | 动作 |
|------|------|
| `expiry_date` 已过 | 从 Milvus 删除（保留在 MinIO 冷存储） |
| 被新版本 `supersedes` | 权重降至 0，30 天后删除 |
| 连续 90 天无检索命中 | 降级到 COLD 存储 |
| 人工标记 `deprecated` | 立即下线 |
| 包含已更正错误 | 标记 `errata`，权重降至 0.1 |

---

## 5. Agent 协作模式扩展

### 5.1 当前模式: Supervisor 委托

```
用户 → Primary Agent → 选择子 Agent → 子 Agent 处理 → 返回 Primary → 响应
```

**局限性**: 一次只能激活一个子 Agent。用户需要同时查航班和酒店时，必须串行。

### 5.2 新增模式一: 并行委托 (Fan-out)

```
用户: "帮我规划下周三去苏黎世的行程，包括航班和酒店"

Primary Agent 同时激活:
  ├─ Flight Agent → search_flights()
  └─ Hotel Agent → search_hotels()
         │
         等待双方完成
         │
         ▼
  Primary Agent 汇总 → 综合推荐
```

**实现方式**: LangGraph `Send` API 或自定义并行节点。

**适用场景**: 独立子任务（查航班 + 查酒店 + 查租车互不依赖）。

### 5.3 新增模式二: 串行依赖链 (Pipeline)

```
用户: "帮我改签到苏黎世的航班，然后在当地订酒店"

Flight Agent → 改签完成 → 通知 Primary
  ↓ (携带新航班到达时间)
Hotel Agent → 根据到达时间搜索酒店 → 返回 Primary
  ↓
Primary 汇总
```

**实现方式**: 子 Agent 不回到 Primary，而是通过 State 传递上下文给下一个 Agent。

**适用场景**: 子任务间有依赖关系（酒店入住时间取决于航班到达时间）。

### 5.4 新增模式三: 协商模式 (Negotiation)

```
用户: "我的预算是 5000 元，帮我安排行程"

Primary Agent:
  ├─ Flight Agent: "最低航班价格 ¥3500"
  ├─ Hotel Agent: "最低酒店价格 ¥2000"
  └─ 超出预算，触发协商:
      Flight Agent: "如果选红眼航班可以降到 ¥2000"
      Hotel Agent: "如果选青旅可以降到 ¥800"
      → 综合方案: ¥2800，在预算内
```

**实现方式**: 子 Agent 共享一个 `budget` 约束，各自在约束下搜索最优方案。Primary Agent 不做选择，而是让子 Agent 相互调整。

**适用场景**: 多目标优化（预算、时间、偏好之间的权衡）。

### 5.5 模式选择逻辑

```
Primary Agent 路由决策:
  1. 用户意图包含多个独立子任务? → 并行委托
  2. 子任务有明确依赖关系? → 串行依赖链
  3. 存在资源约束需要优化? → 协商模式
  4. 单一明确任务? → 当前 Supervisor 委托
```

---

## 6. 用户体验度量

### 6.1 业务指标

技术指标（延迟、错误率、Token 消耗）只能说明系统在运行，不能说明系统在**创造价值**。需要业务维度的度量：

| 指标 | 定义 | 测量方式 | 目标 |
|------|------|---------|------|
| **任务完成率** | 用户是否完成了预订/改签/取消？ | 工具调用成功 + 用户确认 | > 85% |
| **首次解决率** | 一次对话就解决问题的比例 | 对话结束且无需跟进 | > 70% |
| **对话效率** | 完成任务所需的平均轮数 | 对话轮数 / 完成的任务数 | < 5 轮 |
| **降级率** | 多少对话最终转人工？ | 触发 escalation 工具的次数 | < 10% |
| **用户满意度** | 对话后的赞/踩 | 赞 / (赞 + 踩) | > 80% |
| **弃聊率** | 用户中途放弃对话的比例 | 对话中断且未完成任何任务 | < 15% |

### 6.2 用户反馈收集

```
对话结束时:
  ┌────────────────────────────────┐
  │  这次对话对您有帮助吗？         │
  │  👍 有帮助    👎 没帮助          │
  │                                 │
  │  如果没帮助，原因是：            │
  │  ◯ 回答不准确                   │
  │  ◯ 没有理解我的问题              │
  │  ◯ 太慢了                       │
  │  ◯ 缺少我需要的信息              │
  │  ◯ 其他: ___________            │
  └────────────────────────────────┘
```

**反馈 → 动作映射**:

| 反馈原因 | 自动触发动作 |
|---------|------------|
| 回答不准确 | 将该对话加入评估数据集，标记为负样本 |
| 没有理解我的问题 | 检查路由决策是否正确 |
| 太慢了 | 检查延迟指标，考虑模型降级 |
| 缺少我需要的信息 | 触发知识缺口检测 |

### 6.3 用户分群分析

按用户行为将用户分为群组，分析各群组的 Agent 表现：

| 群组 | 特征 | 关注指标 |
|------|------|---------|
| **重度用户** | 月对话 > 50 次 | 满意度趋势、Token 成本 |
| **一次性用户** | 仅 1 次对话 | 首次解决率、为什么不再来？ |
| **投诉用户** | 频繁踩 | 立即人工介入 |
| **沉默用户** | 不反馈 | 主动抽样询问满意度 |

---

## 7. Agent 自检机制

### 7.1 循环检测

Agent 最常见的失败模式: **陷入循环**，反复用不同措辞输出相同内容或重复调用相同工具。

```
循环检测:
  1. 追踪最近 5 轮对话的 embedding
  2. 任意两轮 cosine similarity > 0.95 → 疑似循环
  3. 连续 3 轮 similarity > 0.90 → 确认循环

触发循环后的处理:
  1. Agent 主动声明: "我可能没有完全理解您的需求。"
  2. 提供选项:
     a. "请用不同的方式描述您的问题"
     b. "转接人工客服"
  3. 将循环对话记录到评估数据集
```

### 7.2 冗余工具调用检测

```
检测: 同一工具、相同参数被调用 ≥ 2 次
处理: 第二次调用时 Agent 自问: "我之前已经调用过这个工具，是否需要重新调用？"
      若不需要 → 使用缓存结果
      若需要 (如数据可能已更新) → 告知用户理由
```

### 7.3 置信度自检

```
每轮对话结束后，Agent 自问三个问题:
  1. "我是否确信自己理解了用户的意图？" → 路由置信度
  2. "我检索到的信息是否足够回答这个问题？" → 检索置信度
  3. "我的回答是否完全基于检索到的信息？" → 事实置信度

任一低于 0.7 → 主动标注低置信度
任一低于 0.5 → 拒绝回答，建议转人工
```

### 7.4 健康自检 (Heartbeat)

Agent 定时自检，确保核心依赖可用：

```
每 60 秒执行:
  1. LLM: 发送简单 ping 请求 → 确认模型可用
  2. Milvus: 执行一次简单搜索 → 确认向量数据库可用
  3. MySQL/PostgreSQL: SELECT 1 → 确认数据库可用
  4. Redis: PING → 确认缓存可用

任一失败 → 触发告警 + 启动降级策略
```

---

## 8. 与前序文档的集成

### 8.1 五份文档体系

```
┌──────────────────────────────────────────────────────────────────┐
│                                                                   │
│  upgrade-architecture.md          全局架构升级                     │
│  项目结构 · 配置 · 数据层 · API · Agent · 测试 · Docker 部署       │
│                                                                   │
│  subsystem-redesign.md            核心子系统重设计                  │
│  RAG · 记忆机制 · 用户身份 · 城市映射                              │
│                                                                   │
│  infrastructure-scalability.md    基础设施与扩展性                  │
│  文档管线 · 分布式检索 · HA · 监控 · 缓存 · 网关 · 安全            │
│                                                                   │
│  agent-governance-layered.md      Agent 治理与分层架构             │
│  六层架构 · 评估 · 护栏 · 幻觉检测 · Prompt · 成本                 │
│                                                                   │
│  agent-decision-knowledge.md      决策智能与知识生命周期 ← 本文档   │
│  决策溯源 · 置信度 · 确定性重放 · 知识闭环 · 协作模式 · 自检       │
│                                                                   │
└──────────────────────────────────────────────────────────────────┘
```

### 8.2 本文档如何融入分层架构

```
Layer 6: 治理层 (agent-governance-layered.md)
  ├── 评估体系 ──────→ 依赖 决策溯源 (本文档 §1) 提供评估数据
  ├── 护栏系统 ──────→ 依赖 置信度估计 (本文档 §2) 决定放行/阻断
  ├── 幻觉检测 ──────→ 输出 事实置信度 (本文档 §2.2) 作为输入
  ├── 成本管理 ──────→ 受益于 知识生命周期反馈 (本文档 §4) 优化检索成本
  └── 反馈闭环 ──────→ 依赖 用户反馈 (本文档 §6.2) 驱动优化

Layer 4: 编排层
  ├── 路由决策 ──────→ 依赖 置信度 (本文档 §2) 决定是否澄清
  ├── Handoff 协议 ──→ 扩展为 协作模式 (本文档 §5)
  └── 降级策略 ──────→ 补充 循环检测 (本文档 §7) 触发升级

Layer 1: 基础层
  ├── 向量检索 ──────→ 服务于 知识生命周期 (本文档 §4) 的阶段 5 (服务)
  └── 对象存储 ──────→ 服务于 知识生命周期 (本文档 §4) 的阶段 1 (摄入) 和 7 (废弃)
```

### 8.3 实施优先级

| 阶段 | 内容 | 量级 | 依赖 |
|------|------|------|------|
| **Phase E** | 知识元数据模型 + 决策溯源存储 | 3-4 天 | L1 基础层就绪 |
| **Phase F** | 置信度估计 + 低置信度处理矩阵 | 2-3 天 | L3 Agent 层就绪 |
| **Phase G** | 知识冲突检测 + 知识缺口发现 | 4-5 天 | Milvus + 异步任务就绪 |
| **Phase H** | 确定性重放 + 协作模式扩展 | 3-4 天 | PostgresSaver 就绪 |
| **Phase I** | 用户体验度量 + Agent 自检 | 2-3 天 | 评估体系就绪 |

---

## 附录: 五份文档关键指标覆盖

| 指标维度 | 文档 1 | 文档 2 | 文档 3 | 文档 4 | 文档 5 |
|---------|--------|--------|--------|--------|--------|
| **技术指标** (延迟/错误率/QPS) | ✅ | - | ✅ | - | ✅ |
| **成本指标** (Token/费用) | - | - | - | ✅ | - |
| **质量指标** (忠实性/准确性) | - | - | - | ✅ | - |
| **业务指标** (完成率/满意度) | - | - | - | - | ✅ |
| **决策指标** (路由准确率/置信度) | - | - | - | - | ✅ |
| **知识指标** (覆盖率/时效性/冲突率) | - | - | - | - | ✅ |

---

> **五份文档完整覆盖**: 应用架构 → 核心子系统 → 基础设施 → Agent 治理 → 决策智能与知识生命周期
