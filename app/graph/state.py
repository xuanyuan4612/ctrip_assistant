"""LangGraph 对话状态定义。

该模块定义了多智能体旅行助手的全局 State TypedDict，
包含消息历史、用户身份、对话路由、决策追踪及护栏标记等字段。
"""

from typing import Annotated, Any, Literal, Optional, TypedDict

from langchain_core.messages import AnyMessage
from langgraph.graph import add_messages


# ---------------------------------------------------------------------------
# Reducer helpers
# ---------------------------------------------------------------------------

def update_dialog_stack(left: list[str], right: Optional[str]) -> list[str]:
    """更新对话状态栈的 reducer 函数。

    用于 LangGraph 的 `Annotated` 类型，控制 `dialog_state` 字段的合并逻辑。

    参数:
        left: 当前的状态栈（历史值）。
        right: 新值或特殊操作标识。
               - `None`: 保持不变。
               - `"pop"`: 弹出栈顶元素（回退到上一状态）。
               - 其他字符串: 压入栈中（进入新的子对话）。

    返回:
        更新后的状态栈。
    """
    if right is None:
        return left
    if right == "pop":
        return left[:-1]
    return left + [right]


# ---------------------------------------------------------------------------
# 对话状态
# ---------------------------------------------------------------------------

class State(TypedDict):
    """多智能体旅行助手的全局对话状态。

    字段:
        messages:            消息历史（自动累积，由 `add_messages` 管理去重与追加）。
        summary:             对话摘要（由 LLM 自动生成或更新）。
        user_id:             当前用户的数据库主键。
        username:            当前用户的显示名称。
        passenger_id:        携程乘客 ID（硬编码关联值）。
        user_info:           用户的完整信息字典（姓名、偏好等）。
        dialog_state:        对话路由栈，控制当前处于哪个子助手的上下文中。
        decision_path:       记录 LLM 每次工具选择与路由决策的路径。
        confidence_scores:   各子意图的置信度分数（用于护栏判断）。
        guardrail_flags:     触发的护栏标记列表。
        clarification_needed: 是否需要向用户发起澄清追问。
        collected_slots:     槽位填充过程中已收集的信息键值对。
    """

    messages: Annotated[list[AnyMessage], add_messages]
    summary: str
    user_id: int
    username: str
    passenger_id: str
    user_info: dict
    dialog_state: Annotated[
        list[
            Literal[
                "assistant",
                "update_flight",
                "book_car_rental",
                "book_hotel",
                "book_excursion",
            ]
        ],
        update_dialog_stack,
    ]
    decision_path: list
    confidence_scores: dict
    guardrail_flags: list
    clarification_needed: bool
    collected_slots: dict
