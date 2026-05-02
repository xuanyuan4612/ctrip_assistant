"""图编排层 - 多智能体 LangGraph 工作流。

包含 State 定义、子图路由模型、Agent 节点、工具函数、护栏逻辑、
以及完整的图编排管线（graph.py）和动态代理注册表（registry.py）。

模块结构：
    state.py          - 全局 State TypedDict
    models.py         - 子图路由与任务完成 Pydantic 模型
    graph.py          - 主图构建器 (build_graph / build_default_graph)
    routing.py        - 条件边缘路由函数
    handoff.py        - 入口节点工厂、对话栈弹出、P2P 交接
    interrupts.py     - 人机交互中断管理 (InterruptManager)
    lifecycle.py      - 会话生命周期 (加载用户内存、提取记忆)
    fallback.py       - 降级链 (LLM -> 缓存 -> 规则 -> 人工)
    registry.py       - 动态代理注册表 (AgentRegistry / AgentSpec)
    agents/           - 智能体实现 (BaseAgent, PrimaryAgent, 领域代理)
    tools/            - 工具层 (ToolResult, ToolNode, 业务工具)
    guardrails/       - 护栏逻辑
"""

# ---- 图构建 ------------------------------------------------------------
from app.graph.graph import build_graph, build_default_graph, build_sub_graph, SubAgentSpec

# ---- 路由 ----------------------------------------------------------------
from app.graph.routing import (
    route_by_intent,
    route_primary_assistant,
    route_sub_agent,
    route_to_workflow,
)

# ---- 交接协议 ------------------------------------------------------------
from app.graph.handoff import create_entry_node, pop_dialog_state, direct_agent_handoff

# ---- 中断管理 ------------------------------------------------------------
from app.graph.interrupts import InterruptManager, interrupt_manager, build_approval_prompt, is_approval_input

# ---- 生命周期 ------------------------------------------------------------
from app.graph.lifecycle import load_user_info, load_user_memory, extract_memories, summarize, SummarizationNode

# ---- 降级链 --------------------------------------------------------------
from app.graph.fallback import FallbackChain, fallback_chain, create_fallback_tool_node

# ---- 代理注册表 ----------------------------------------------------------
from app.graph.registry import AgentRegistry, AgentSpec, registry, create_default_registry

# ---- 状态 -----------------------------------------------------------------
from app.graph.state import State, update_dialog_stack

# ---- 模型 -----------------------------------------------------------------
from app.graph.models import (
    CompleteOrEscalate,
    ToFlightBookingAssistant,
    ToBookCarRental,
    ToHotelBookingAssistant,
    ToBookExcursion,
)

__all__ = [
    "build_graph",
    "build_default_graph",
    "build_sub_graph",
    "SubAgentSpec",
    "route_by_intent",
    "route_primary_assistant",
    "route_sub_agent",
    "route_to_workflow",
    "create_entry_node",
    "pop_dialog_state",
    "direct_agent_handoff",
    "InterruptManager",
    "interrupt_manager",
    "build_approval_prompt",
    "is_approval_input",
    "load_user_info",
    "load_user_memory",
    "extract_memories",
    "summarize",
    "SummarizationNode",
    "FallbackChain",
    "fallback_chain",
    "create_fallback_tool_node",
    "AgentRegistry",
    "AgentSpec",
    "registry",
    "create_default_registry",
    "State",
    "update_dialog_stack",
    "CompleteOrEscalate",
    "ToFlightBookingAssistant",
    "ToBookCarRental",
    "ToHotelBookingAssistant",
    "ToBookExcursion",
]
