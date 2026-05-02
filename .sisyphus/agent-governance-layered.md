# Agent 治理与分层架构设计

> **版本**: v1.0  
> **日期**: 2026-04-28  
> **关联文档**: `upgrade-architecture.md` / `subsystem-redesign.md` / `infrastructure-scalability.md`  
> **定位**: Agent 架构师视角 —— 补齐治理层 + 分层重构 + 生产细节完善  

---

## 目录

1. [为什么必须分层](#1-为什么必须分层)
2. [六层目标架构](#2-六层目标架构)
3. [Layer 6: 治理层 (新增)](#3-layer-6-治理层)
   - [3.1 Agent 评估体系](#31-agent-评估体系)
   - [3.2 护栏系统](#32-护栏系统)
   - [3.3 幻觉检测](#33-幻觉检测)
   - [3.4 Prompt 管理](#34-prompt-管理)
   - [3.5 成本管理](#35-成本管理)
   - [3.6 反馈闭环](#36-反馈闭环)
4. [Layer 5: 表现层 (细化)](#4-layer-5-表现层)
5. [Layer 4: 编排层 (细化)](#5-layer-4-编排层)
6. [Layer 3: Agent 层 (细化)](#6-layer-3-agent-层)
7. [Layer 2: 能力层 (细化)](#7-layer-2-能力层)
8. [Layer 1: 基础层 (细化)](#8-layer-1-基础层)
9. [各层接口契约](#9-各层接口契约)
10. [与前序文档的衔接](#10-与前序文档的衔接)

---

## 1. 为什么必须分层

### 1.1 当前架构的扁平化问题

三份前序文档中，Agent 系统的设计仍是扁平化的——核心代码集中在 `graph.py` 和 `agents/` 目录，混杂了：

- **状态定义**（State TypedDict）——属于编排层
- **路由逻辑**（条件边/条件函数）——属于编排层
- **Prompt 模板**（ChatPromptTemplate）——属于 Agent 层
- **工具绑定**（llm.bind_tools）——属于 Agent 层
- **LLM 客户端配置**——属于基础层

这种扁平结构的后果：

| 问题 | 具体表现 | 生产影响 |
|------|---------|---------|
| **变更爆炸半径大** | 改一个 Prompt 要重新部署整个图 | 发布风险高，回滚粒度粗 |
| **无法独立测试** | Prompt 质量、路由准确性、工具正确性混在一起 | Bug 定位困难，评估无法隔离 |
| **无法独立扩缩** | 所有 Agent 共享同一部署单元 | 高频 Agent 拖慢低频 Agent |
| **无法独立评估** | 无法单独评估"主 Agent 路由是否准确" | 优化无从下手 |
| **团队协作瓶颈** | Prompt 工程师、工具开发者、编排者改同一文件 | 开发效率低 |

### 1.2 分层原则

| 原则 | 说明 |
|------|------|
| **单向依赖** | 上层依赖下层，下层不感知上层 |
| **接口契约** | 每层通过明确的接口/协议交互，不跨层访问 |
| **独立可测试** | 每层可 mock 下层进行隔离测试 |
| **独立可部署** | Agent 层（最高频变更）可独立发布，不影响编排层 |
| **横切治理** | 评估、护栏、监控通过横切面注入，Agent 开发者无需感知 |

---

## 2. 六层目标架构

```
┌──────────────────────────────────────────────────────────────┐
│                                                               │
│  Layer 6:  治理层 (Governance)         ← 横切所有层           │
│  ────────────────────────────────────                         │
│  评估体系 · 护栏系统 · 幻觉检测 · Prompt 管理 · 成本管理 · 反馈闭环 │
│                                                               │
├──────────────────────────────────────────────────────────────┤
│                                                               │
│  Layer 5:  表现层 (Presentation)                              │
│  ──────────────────────────────                               │
│  FastAPI 路由 · WebSocket 流式输出 · 请求/响应 Schema ·        │
│  输入验证 · Session 管理 · 错误格式化                          │
│                                                               │
├──────────────────────────────────────────────────────────────┤
│                                                               │
│  Layer 4:  编排层 (Orchestration)                             │
│  ────────────────────────────────                             │
│  State 定义 · StateGraph 拓扑 · 路由决策 · 条件边 ·           │
│  人机交互中断 · 子图生命周期 · Handoff 协议 · 降级策略         │
│                                                               │
├──────────────────────────────────────────────────────────────┤
│                                                               │
│  Layer 3:  Agent 层 (Agent)                                   │
│  ────────────────────────────                                 │
│  Prompt 模板 · LLM 绑定 · 工具选择策略 · 输出解析 ·            │
│  子 Agent 定义 · 多模型路由 · Token 预算                       │
│                                                               │
├──────────────────────────────────────────────────────────────┤
│                                                               │
│  Layer 2:  能力层 (Capability)                                │
│  ─────────────────────────────                                │
│  Tool 定义 (@tool) · 参数 Schema · 执行逻辑 ·                  │
│  数据校验 · 错误标准化 · 审计日志                              │
│                                                               │
├──────────────────────────────────────────────────────────────┤
│                                                               │
│  Layer 1:  基础层 (Foundation)                                │
│  ─────────────────────────────                                │
│  LLM Provider 抽象 · 记忆存储 (Checkpoint + Store) ·           │
│  向量检索 (Milvus) · 缓存 (Redis) · 对象存储 (MinIO) ·         │
│  数据库连接池 · 消息队列                                       │
│                                                               │
└──────────────────────────────────────────────────────────────┘
```

### 各层关键属性

| 层 | 变更频率 | 测试策略 | 独立部署 | 负责人 |
|----|---------|---------|---------|--------|
| L6 治理 | 低 | 配置验证 + 集成测试 | 否（横切注入） | 平台团队 |
| L5 表现 | 低 | API 集成测试 | 否 | 后端团队 |
| L4 编排 | 中 | 路由正确性单元测试 + 集成测试 | 是 | Agent 架构师 |
| L3 Agent | **高** | Prompt 离线评估 + A/B 测试 | **是（独立发布）** | Prompt 工程师 |
| L2 能力 | 中 | 工具函数单元测试 | 是 | 后端团队 |
| L1 基础 | 低 | 连接/性能测试 | 否 | 平台/DevOps |

---

## 3. Layer 6: 治理层

治理层是**当前三份文档完全缺失**的部分。它是横切面，不单独部署，而是通过中间件、钩子、回调注入到其他各层。

### 3.1 Agent 评估体系

#### 3.1.1 三层评估矩阵

生产级 Agent 系统的评估必须覆盖三个维度：

```
类型 1: 行为检查 (Behavior Checks) — 无需标准答案
  - 语气是否合规？格式是否正确？
  - 输出是否包含禁止内容？
  - 适用于每一次对话

类型 2: 上下文检查 (Context-Based Checks) — 需要上下文
  - 输出是否基于检索到的文档？（忠实性）
  - Agent 是否调用了正确的工具？
  - 捕获"调对了工具但编造了结果"的幻觉

类型 3: 标准答案检查 (Ground-Truth Checks) — 需要标注数据
  - 预期工具调用序列是否正确？
  - 输出与参考答案语义是否匹配？
  - 用于 CI/CD 回归测试门禁
```

#### 3.1.2 评估成熟度模型

```
Phase 1: 人工审查
  - 抽查对话日志
  - 发现问题 → 修复 Prompt

Phase 2: 在线评估
  - 实时流量上运行 LLM-as-Judge 评分
  - 监控指标: 忠实性得分、用户满意度
  - 趋势下降 → 告警

Phase 3: 离线评估
  - 维护标注数据集 (100+ 条真实对话)
  - 每次 Prompt 变更前运行回归评估
  - CI/CD 门禁: 得分 < 0.85 → 阻断合并
```

#### 3.1.3 核心指标

| 指标 | 含义 | 告警阈值 |
|------|------|---------|
| **忠实性 (Faithfulness)** | 输出是否基于检索文档 | < 0.85 (下降趋势) |
| **回答相关性 (Answer Relevance)** | 输出是否回答了问题 | < 0.80 |
| **上下文精确率 (Context Precision)** | 检索结果是否相关 | < 0.75 |
| **工具选择准确率** | Agent 是否选了正确的工具 | < 0.90 |
| **路由准确率** | 主 Agent 是否路由到正确的子 Agent | < 0.90 |
| **轨迹效率** | 实际步骤数 / 理想步骤数 | > 2.0 (过度低效) |

#### 3.1.4 CI/CD 评估门禁

```
PR 提交 → 单元测试 → 集成测试 → 离线评估 → 门禁检查
                                          ↓
                              得分 >= 0.85 → 允许合并
                              得分 < 0.85  → 阻断 + 通知
```

### 3.2 护栏系统

#### 3.2.1 五层纵深防御

```
Layer 1: 快速确定性检查 (毫秒级)
  工具: regex + Presidio + 分类器
  覆盖: PII 检测、敏感词过滤、格式校验

Layer 2: 小型模型分类 (百毫秒级)
  工具: Llama Guard / NeMo self_check
  覆盖: 内容安全、主题控制、越狱检测

Layer 3: Agent 执行护栏 (内嵌)
  工具: NeMo GuardrailsMiddleware (每个节点)
  覆盖: 工具调用权限、参数校验、输出审核

Layer 4: 输出后验证 (秒级)
  工具: 幻觉检测 + 事实性校验
  覆盖: 生成内容是否与检索文档一致

Layer 5: 人机协同 (最终防线)
  工具: LangGraph interrupt()
  覆盖: 高风险操作需用户确认
```

#### 3.2.2 严重度分级处理

| 严重度 | 类型 | 处理动作 |
|--------|------|---------|
| 4 | 与上下文矛盾 | **阻断响应**，替换为免责声明 |
| 3 | 虚构信息 | **阻断** (模型添加了上下文之外的信息) |
| 2 | 不可验证 | 软处理: 添加置信度标注，标记人工审核 |
| 1 | 推测性表述 | 仅记录日志，UI 添加置信度指示 |
| 0 | 文档支撑 | 直接放行 |

### 3.3 幻觉检测

#### 3.3.1 四层检测栈

```
Layer 1: 忠实性检查 (最粗)
  - 将输出分解为原子声明
  - 逐条检查是否被检索文档支撑
  - 得分 0-1，阈值 0.7

Layer 2: 矛盾检查
  - 检查输出是否与检索文档**主动矛盾**
  - 比忠实性更昂贵，但捕获不同失败模式

Layer 3: 引用验证 (最精确)
  - 验证每个引用的来源是否确实支持对应声明
  - 最精确但也最昂贵

Layer 4: Token 级检测
  - 逐 Token 标注: 有支撑 / 无支撑
  - 精确定位缺乏事实依据的具体文本片段
```

#### 3.3.2 设计要点

- NLI 模型用于生产（快速、准确、廉价）
- LLM-as-Judge 用于最高精度场景（更慢、更贵）
- 不确定时不回答（Abstention）优于给出错误答案
- 幻觉检测结果反馈到评估数据集，持续改进

### 3.4 Prompt 管理

#### 3.4.1 版本化策略

**核心原则**: Prompt 是版本化制品，不是字符串。

```
开发环境: 拉取最新版本
  prompt = hub.pull("org/rag-answer-prompt")

生产环境: 锁定到 commit hash
  prompt = hub.pull("org/rag-answer-prompt:abc123def456")

回滚: 改 hash → 重启进程 (无需代码部署)
```

#### 3.4.2 变更工作流

```
Prompt 工程师修改 Prompt
  → 推送到 Prompt Hub (创建不可变 commit)
  → Webhook 触发 CI 离线评估
  → 评估通过 → 部署到 Staging
  → 在线评估 + A/B 测试
  → 通过 → 提升到 Production 标签
  → 失败 → 自动回滚
```

#### 3.4.3 A/B 测试框架

- 流量分割: 10% 走新 Prompt，90% 走基线
- 比较指标: 忠实性、用户满意度、任务完成率
- 统计显著后决定是否全量

#### 3.4.4 自动优化 (DSPy)

- 每月运行 MIPROv2 自动优化器
- 搜索指令候选 + Few-shot 示例 + 贝叶斯优化
- 在留出验证集上评分
- 人工审查后决定是否上线

### 3.5 成本管理

#### 3.5.1 多模型路由

```
用户查询 → 复杂度分类器 (8 个信号)
  ├── 简单 (70%): GPT-4.1 Nano ($0.05/$0.20 per M tokens)
  ├── 中等 (25%): Claude Haiku 4.5 ($1.00/$5.00)
  └── 复杂 (5%):  Claude Sonnet 4.6 ($3.00/$15.00)

综合成本节省: 60-80%
```

**8 个分类信号**: 消息长度、对话深度、工具使用模式、推理深度要求、领域特异性、行动风险等级、语言复杂度、代码存在性。

#### 3.5.2 语义缓存

- L1 精确缓存: MD5(query + model + top_k) → 命中率 5-10%，延迟 ~1ms
- L2 语义缓存: pgvector cosine > 0.92 → 命中率 20-35%，延迟 ~50ms
- 综合节省: **60-68% LLM 调用**

#### 3.5.3 Token 预算

| 维度 | 限制 |
|------|------|
| 单用户/日 | 100K tokens |
| 单用户/会话 | 50K tokens |
| Agent 推理深度 | 16K tokens 上限 |
| 每日总预算告警 | 达到 80% → Warning，100% → 限流 |

#### 3.5.4 成本归因

每个 Agent 调用记录:
- 模型名称 + Token 数 + 费用
- 按用户 / 会话 / Agent / 工具 / 日期维度聚合
- Grafana 仪表盘实时展示
- 异常检测: 单日费用突增 2x → 告警

### 3.6 反馈闭环

```
生产对话日志
  │
  ├── 用户反馈 (赞/踩) → 自动标注
  ├── 低分对话 → 人工审核队列
  └── 护栏触发记录 → 问题分类
         │
         ▼
  标注数据集更新 (自动 + 人工)
         │
         ▼
  每月 DSPy 重新优化 Prompt
         │
         ▼
  离线评估 → CI 门禁 → 灰度发布
```

---

## 4. Layer 5: 表现层

### 4.1 职责边界

| 应该做 | 不应该做 |
|--------|---------|
| HTTP 协议适配 (REST + WebSocket) | 不应包含 Agent 逻辑 |
| 请求参数校验 (Pydantic Schema) | 不应直接调用 LLM |
| 响应格式化 (统一错误格式) | 不应做路由决策 |
| Session 创建和恢复 | 不应管理 Agent State |
| 构建 Runtime Context (注入用户身份) | 不应写 Prompt |

### 4.2 API 端点设计 (最终版)

```
POST   /api/v1/auth/register        # 用户注册
POST   /api/v1/auth/login           # 用户登录 (JSON)
POST   /api/v1/auth/token           # OAuth2 表单 (Swagger)
POST   /api/v1/auth/refresh         # 刷新 Token
POST   /api/v1/auth/logout          # 登出 (Token 黑名单)

GET    /api/v1/users                # 用户列表 (分页)
GET    /api/v1/users/{user_id}      # 用户详情
PATCH  /api/v1/users/{user_id}      # 更新用户
DELETE /api/v1/users                # 批量删除

POST   /api/v1/graph/chat           # 多智能体对话 (流式)
GET    /api/v1/graph/sessions       # 用户会话列表
GET    /api/v1/graph/sessions/{id}  # 会话详情/恢复
DELETE /api/v1/graph/sessions/{id}  # 删除会话

GET    /api/v1/health               # 健康检查
GET    /api/v1/metrics              # Prometheus 指标
```

### 4.3 流式输出设计

```
POST /api/v1/graph/chat
  → 返回 Server-Sent Events (SSE):
    event: thinking
    data: {"agent": "primary_assistant", "status": "analyzing"}

    event: tool_call
    data: {"tool": "search_flights", "args": {...}}

    event: interrupt
    data: {"message": "AI助手即将执行改签操作，是否确认？", "requires": "confirmation"}

    event: token
    data: {"content": "为您找到以下航班..."}

    event: done
    data: {"session_id": "...", "cost": {"tokens": 1234, "amount": 0.05}}
```

### 4.4 错误响应格式

```json
{
  "error": {
    "code": "LLM_SERVICE_UNAVAILABLE",
    "message": "AI 服务暂时不可用，请稍后重试",
    "request_id": "req_abc123",
    "timestamp": "2026-04-28T10:30:00Z"
  }
}
```

---

## 5. Layer 4: 编排层

### 5.1 职责边界

| 应该做 | 不应该做 |
|--------|---------|
| 定义 State 结构和 Reducer | 不应写 Prompt 内容 |
| 定义图拓扑 (节点 + 边) | 不应直接调用 LLM |
| 路由决策逻辑 | 不应处理 HTTP 请求 |
| 人机交互中断处理 | 不应实现工具逻辑 |
| 子图生命周期管理 | 不应管理数据库连接 |

### 5.2 子 Agent 间通信协议 (Handoff Protocol)

当前只有 `CompleteOrEscalate` 一种退出方式。生产级需要标准化的 Handoff 协议：

```
Handoff 请求 (主 Agent → 子 Agent):
  {
    "type": "handoff",
    "from": "primary_assistant",
    "to": "flight_agent",
    "context": {
      "user_intent": "改签航班",
      "relevant_info": "用户想从北京飞苏黎世，改签到下周三"
    }
  }

Handoff 响应 (子 Agent → 主 Agent):
  {
    "type": "handoff_response",
    "from": "flight_agent",
    "to": "primary_assistant",
    "status": "completed" | "escalated" | "needs_clarification",
    "result": "已成功改签",
    "context": { ... }
  }
```

### 5.3 降级策略链

```
用户请求
  │
  ▼
LLM 调用 → 成功? → 正常响应
  │ 失败
  ▼
语义缓存 → 命中? → 返回缓存结果 (标注"可能不完全准确")
  │ 未命中
  ▼
规则引擎 → 匹配? → 返回预定义响应
  │ 无匹配
  ▼
转人工 / 返回兜底回复: "抱歉，我暂时无法处理您的请求，请稍后重试或联系人工客服"
```

### 5.4 多轮澄清循环

当前一次性路由不支持情况澄清。生产需要 Clarification Loop:

```
用户: "帮我查航班"
Agent: "请问您要从哪个城市出发，飞往哪里？"
用户: "北京到上海"
Agent: "出行日期是？"
用户: "下周三"
Agent: (已收集足够信息，执行搜索)
```

**实现**: 在 State 中增加 `clarification_needed` 和 `collected_slots` 字段，路由函数检测是否需要澄清。

### 5.5 编排层目录结构

```
app/graph/
  ├── state.py              # State TypedDict + Reducer
  ├── graph.py              # 图构建 (拓扑定义)
  ├── routing.py            # 路由函数 (条件边逻辑)
  ├── interrupts.py         # 人机交互中断处理
  ├── handoff.py            # Agent 间通信协议
  ├── lifecycle.py          # 子图生命周期管理
  └── fallback.py           # 降级策略链
```

---

## 6. Layer 3: Agent 层

### 6.1 职责边界

| 应该做 | 不应该做 |
|--------|---------|
| 定义 Prompt 模板 | 不应定义图拓扑 |
| LLM 与工具绑定 | 不应直接操作数据库 |
| 输出解析 | 不应处理 HTTP 请求 |
| 工具选择策略 | 不应管理连接池 |

### 6.2 Agent 层目录结构

```
app/graph/agents/
  ├── base.py               # Agent 基类 (重试、超时、护栏钩子)
  ├── prompts/               # Prompt 仓库 (版本化管理)
  │   ├── primary.py        # 主 Agent Prompt
  │   ├── flight.py         # 航班 Agent Prompt
  │   ├── hotel.py          # 酒店 Agent Prompt
  │   ├── car_rental.py     # 租车 Agent Prompt
  │   └── excursion.py      # 旅行 Agent Prompt
  ├── primary.py            # 主 Agent Runnable
  ├── flight.py             # 航班 Agent Runnable
  ├── hotel.py              # 酒店 Agent Runnable
  ├── car_rental.py         # 租车 Agent Runnable
  ├── excursion.py          # 旅行 Agent Runnable
  ├── router.py             # 多模型路由 (复杂度分类器)
  └── evaluator.py          # Agent 自评估 (内嵌评分)
```

### 6.3 Agent 基类设计

```python
class BaseAgent:
    """所有 Agent 的基类，提供统一的重试/超时/护栏钩子"""

    def __init__(self, runnable, guardrail=None, max_retries=3, timeout=60):
        self.runnable = runnable
        self.guardrail = guardrail
        self.max_retries = max_retries
        self.timeout = timeout

    def invoke(self, state, config):
        # 1. 护栏: 输入检查
        if self.guardrail:
            self.guardrail.check_input(state)

        # 2. 带重试和超时的 LLM 调用
        for attempt in range(self.max_retries):
            try:
                with timeout(self.timeout):
                    result = self.runnable.invoke(state)
                break
            except TimeoutError:
                if attempt == self.max_retries - 1:
                    raise
            except Exception:
                if attempt == self.max_retries - 1:
                    raise
                time.sleep(2 ** attempt)

        # 3. 护栏: 输出检查
        if self.guardrail:
            self.guardrail.check_output(result)

        # 4. 内嵌评估 (异步)
        self._schedule_evaluation(state, result)

        return result
```

### 6.4 Prompt 与代码分离

**分离前（当前）**:
```python
# agent_assistant.py — Prompt 和代码混在一起
flight_booking_prompt = ChatPromptTemplate.from_messages([
    ("system", "您是专门处理航班查询..."),
    ("placeholder", "{messages}"),
])
update_flight_runnable = flight_booking_prompt | llm.bind_tools(...)
```

**分离后**:
```python
# agents/prompts/flight.py — 纯 Prompt 定义
FLIGHT_SYSTEM_PROMPT = """
您是专门处理航班查询、改签和预定的助理。
当用户需要帮助更新他们的预订时，主助理会将工作委托给您。
请与客户确认更新后的航班详情，并告知他们任何额外费用。
...
当前用户的航班信息:
<Flights>
{user_info}
</Flights>
当前时间: {time}
"""

# agents/flight.py — Agent 逻辑
class FlightAgent(BaseAgent):
    def __init__(self, llm_provider):
        prompt = ChatPromptTemplate.from_messages([
            ("system", FLIGHT_SYSTEM_PROMPT),
            ("placeholder", "{messages}"),
        ])
        tools = [search_flights, update_ticket, cancel_ticket, CompleteOrEscalate]
        runnable = prompt | llm_provider.get_chat_model().bind_tools(tools)
        super().__init__(runnable=runnable)
```

---

## 7. Layer 2: 能力层

### 7.1 职责边界

| 应该做 | 不应该做 |
|--------|---------|
| 定义工具函数 (@tool) | 不应做路由决策 |
| 参数 Schema 与校验 | 不应写 Prompt |
| 执行业务逻辑 | 不应管理图生命周期 |
| 标准化错误返回 | 不应直接响应 HTTP |

### 7.2 工具分类

```
app/graph/tools/
  ├── business/             # 业务工具
  │   ├── flights.py        # 航班搜索/改签/取消
  │   ├── hotels.py         # 酒店搜索/预订/取消
  │   ├── car_rentals.py    # 租车搜索/预订/取消
  │   └── excursions.py     # 旅行搜索/预订/取消
  ├── knowledge/            # 知识检索工具
  │   ├── policy.py         # RAG 政策查询
  │   └── faq.py            # FAQ 检索
  ├── system/               # 系统工具
  │   ├── escalation.py     # 升级到主 Agent
  │   └── clarification.py  # 请求用户澄清
  └── handler.py            # 工具节点 + Fallback
```

### 7.3 工具设计规范

每个工具遵循统一契约:

```python
@tool
def book_hotel(
    hotel_id: int,
    runtime: ToolRuntime[UserContext, State],
) -> ToolResult:
    """
    预订酒店。

    Args:
        hotel_id: 要预订的酒店 ID

    Returns:
        ToolResult: 包含 status (success/error) 和 message
    """
    # 1. 身份校验 (审计)
    user_id = runtime.context.user_id
    _audit("book_hotel", user_id, {"hotel_id": hotel_id})

    # 2. 业务逻辑
    try:
        repo = HotelRepository()
        result = repo.book(hotel_id, user_id)
        return ToolResult(status="success", message=f"酒店 {hotel_id} 预订成功")
    except Exception as e:
        return ToolResult(status="error", message=str(e))
```

---

## 8. Layer 1: 基础层

### 8.1 职责边界

| 应该做 | 不应该做 |
|--------|---------|
| LLM Provider 抽象 | 不应包含业务逻辑 |
| 数据库连接池管理 | 不应感知 Agent 存在 |
| 向量存储 (Milvus) | 不应做分块决策 |
| 缓存 (Redis) | 不应写 Prompt |
| 对象存储 (MinIO) | 不应做工具选择 |

### 8.2 基础层目录结构

```
app/infrastructure/
  ├── llm/
  │   ├── base.py           # AbstractLLMProvider
  │   ├── openai.py         # OpenAI
  │   └── deepseek.py       # DeepSeek
  ├── db/
  │   ├── engine_mysql.py   # MySQL 连接池
  │   ├── engine_pg.py      # PostgreSQL 连接池 (Checkpoint + Store)
  │   └── redis.py          # Redis 连接
  ├── vector/
  │   └── milvus.py         # Milvus 客户端封装
  ├── storage/
  │   └── minio.py          # MinIO 客户端封装
  ├── cache/
  │   ├── exact.py          # L1 精确缓存
  │   └── semantic.py       # L2 语义缓存
  └── queue/
      ├── celery_app.py     # Celery 配置
      └── tasks.py          # 异步任务定义
```

---

## 9. 各层接口契约

### 9.1 L5 → L4 (表现层 → 编排层)

```python
# 表现层调用编排层
from app.graph.graph import TravelGraph
from app.graph.state import State
from app.infrastructure.llm.context import UserContext

graph = TravelGraph()

# 构建 Runtime Context (从 JWT 解析)
context = UserContext(
    user_id=user_id,
    username=username,
    passenger_id=passenger_id,
)

# 调用编排层
result = await graph.invoke(
    input={"messages": [HumanMessage(content=user_input)]},
    config={"configurable": {"thread_id": thread_id}},
    context=context,
)
```

### 9.2 L4 → L3 (编排层 → Agent 层)

```python
# 编排层调用 Agent 层
from app.graph.agents.flight import FlightAgent

flight_agent = FlightAgent(llm_provider)

# 编排层不关心 Agent 内部的 Prompt 和工具绑定
# 只关心: 给定 State → 返回新 State
result = flight_agent.invoke(state, config)
```

### 9.3 L3 → L2 (Agent 层 → 能力层)

```python
# Agent 层通过工具绑定间接调用能力层
# Agent 不直接 import 工具，而是通过 llm.bind_tools() 注册
# 工具的执行由编排层的 ToolNode 负责
```

### 9.4 L1 → All (基础层提供给所有上层)

```python
# 所有上层通过依赖注入获取基础层资源
# 不直接实例化连接，而是通过 FastAPI Depends 注入
async def get_llm():
    return LLMProviderFactory.create(settings.LLM_PROVIDER)

async def get_db_session():
    async with AsyncSessionLocal() as session:
        yield session
```

---

## 10. 与前序文档的衔接

### 10.1 四份文档体系

```
┌─────────────────────────────────────────────────────────────┐
│  upgrade-architecture.md                                     │
│  全局架构升级: 项目结构 · 配置 · 数据层 · API · Agent · 部署  │
├─────────────────────────────────────────────────────────────┤
│  subsystem-redesign.md                                       │
│  核心子系统: RAG · 记忆机制 · 用户身份 · 城市映射             │
├─────────────────────────────────────────────────────────────┤
│  infrastructure-scalability.md                               │
│  基础设施: 文档管线 · 分布式检索 · HA · 监控 · 缓存 · 安全    │
├─────────────────────────────────────────────────────────────┤
│  agent-governance-layered.md (本文档)                         │
│  Agent 治理: 分层架构 · 评估 · 护栏 · 幻觉检测 · Prompt · 成本│
└─────────────────────────────────────────────────────────────┘
```

### 10.2 本文档补充的具体细节

| 前序文档遗留 | 本文档补充 |
|-------------|-----------|
| Prompt 散落在代码中 | **L3 Agent 层**: Prompt 与代码分离 + 版本化管理 |
| 无 Agent 评估机制 | **L6.1**: 三层评估矩阵 + CI/CD 门禁 |
| 无安全护栏 | **L6.2**: 五层纵深防御 + 严重度分级处理 |
| 无幻觉检测 | **L6.3**: 四层检测栈 + Abstention 机制 |
| 无成本控制 | **L6.5**: 多模型路由 + 语义缓存 + Token 预算 |
| 子 Agent 通信不标准 | **L5.2**: Handoff 协议 |
| 无降级策略 | **L5.3**: LLM → 缓存 → 规则 → 转人工 |
| 一次性路由 | **L5.4**: 多轮澄清循环 |
| Agent 之间无分层 | **全文**: 六层架构 + 接口契约 |
| 无反馈闭环 | **L6.6**: 生产 → 标注 → 优化 → 评估 → 发布 |

### 10.3 实施优先级

| 阶段 | 内容 | 量级 |
|------|------|------|
| **Phase A** (立即) | L6 评估体系 + L6 护栏 Layer 1-2 + L3 Prompt 分离 | 3-5 天 |
| **Phase B** (短期) | L6 成本管理 + L6 幻觉检测 + L4 Handoff 协议 | 5-7 天 |
| **Phase C** (中期) | L6 护栏 Layer 3-5 + L4 降级策略 + L4 澄清循环 | 5-7 天 |
| **Phase D** (持续) | L6 反馈闭环 + L6 Prompt 自动优化 + A/B 测试 | 持续迭代 |

---

> **四份文档完整覆盖**: 应用架构 → 核心子系统 → 基础设施与扩展性 → Agent 治理与分层
