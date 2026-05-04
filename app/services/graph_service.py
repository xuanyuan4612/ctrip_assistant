# -*- coding: utf-8 -*-
"""
多智能体对话编排服务（GraphService）

本模块是 AI 多智能体对话系统的核心编排层，负责：
  1. 用户身份解析与携程乘客信息绑定（resolve_identity）
  2. LangGraph StateGraph 的构建与执行调度（execute）
  3. 对话上下文管理（thread_id 驱动的会话续传）

设计模式：服务层（Service Layer）
  - 将 Graph 编排逻辑从 API 端点中分离
  - 处理身份解析、异常捕获、结果格式化等横切关注点
  - API 端点（graph.py）只负责 HTTP 协议层（REST/SSE）

LangGraph 集成说明：
  - 使用 LangGraph 的 StateGraph 构建多 Agent 协作流程
  - 流程：分类器（Classifier）→ Supervisor → 各领域 Agent → 汇总
  - stream_mode="values" 表示每次状态更新时返回完整状态快照
  - config 中的 thread_id 用于 checkpoint（状态持久化），支持多轮对话
"""
import logging
import uuid

from fastapi import Request

from app.core.exceptions import AuthenticationError

log = logging.getLogger("app.services.graph")


class GraphService:
    """
    Graph 编排服务类

    所有方法均为静态方法，可直接调用。

    核心方法：
      - resolve_identity: 从 HTTP 请求解析用户身份（JWT → 用户信息）
      - execute: 执行多智能体对话（LangGraph 引擎调用）
    """

    @staticmethod
    def resolve_identity(request: Request) -> tuple:
        """
        从 HTTP 请求解析用户身份

        身份解析链：
          AuthMiddleware → JWT 解码 → request.state.username → resolve_identity

          JWT 令牌 → 解码 → "{user_id}:{username}"
                              ↓
                          按 ":" 分割
                              ↓
                    user_id     username
                              ↓
                    UserRepository.get_by_username_raw
                              ↓
                    passenger_id（携程乘客编号）

        流程说明：
          1. 从 request.state.username 获取 JWT 中存储的 "{user_id}:{username}"
             （该值由 AuthMiddleware 在验证 JWT 后设置）
          2. 按 ":" 分割得到 user_id 和 username
          3. 从数据库查询用户的 passenger_id（用于携程 API 调用）
             - passenger_id 是用户在携程平台绑定的乘客编号
             - 用于查询航班、酒店等操作时的身份标识

        Args:
            request: FastAPI 请求对象（已由 AuthMiddleware 注入用户信息）

        Returns:
            tuple: (user_id: int, username: str, passenger_id: str)

        Raises:
            AuthenticationError: 用户身份标识格式无效（缺少 ":" 分隔符）
        """
        # 第一步：从 request.state 获取用户标识
        # 格式："{user_id}:{username}"，例如 "42:zhangsan"
        raw = getattr(request.state, "username", "")

        # 第二步：验证格式
        if ":" not in raw:
            raise AuthenticationError("无效的用户身份")

        # 第三步：解析 user_id 和 username
        user_id_str, username = raw.split(":", 1)
        user_id = int(user_id_str)

        # 第四步：查询数据库获取 passenger_id
        # UserRepository.get_by_username_raw 根据 user_id 查询用户
        # passenger_id 用于绑定携程乘客身份，执行具体业务操作
        from app.db.repositories.user import UserRepository
        user = UserRepository().get_by_username_raw(user_id)
        passenger_id = user.passenger_id if user and user.passenger_id else ""

        return user_id, username, passenger_id

    @staticmethod
    async def execute(user_input: str, user_id: int, username: str, passenger_id: str, thread_id: str = None) -> dict:
        """
        执行多智能体对话

        这是整个 AI 系统的核心调用入口。流程如下：

        1. 线程管理：
           - 如果未提供 thread_id，创建一个新的（格式：user_{user_id}:{uuid}）
           - thread_id 是 LangGraph checkpoint 的键，用于恢复对话状态
           - WHY：支持多轮对话，每次请求使用相同 thread_id 可延续上下文

        2. LangGraph 图构建与执行：
           a. build_default_graph() 构建完整的 StateGraph
              - 包含分类器（Classifier）、Supervisor、各领域 Agent
           b. 创建 UserContext，包含用户身份和携程乘客信息
           c. 配置 config 包含 thread_id 和 user_context
           d. 根据输入内容分支：
              - "y"（批准操作）：传入 None，继续未完成的操作流程
              - 其他输入：包装为 ("user", input) 消息对开始新对话
           e. stream_mode="values"：每次状态更新返回完整状态
              - WHY：方便从任意节点提取最新的消息内容

        3. 结果提取：
           - 遍历所有事件，提取最后一条消息的 content
           - 如果结果为空的特殊处理：
             - 图可能等待用户确认（interrupt 状态）
             - 返回提示信息引导用户输入 "y" 确认

        4. 异常处理：
           - 任何异常都会捕获并记录完整堆栈
           - 返回包含错误摘要的友好消息（截断至 100 字符）
           - WHY：防止将 LLM API 密钥等敏感信息暴露给用户

        Args:
            user_input: 用户输入文本
            user_id: 用户数字 ID
            username: 用户名
            passenger_id: 携程乘客 ID
            thread_id: 会话线程 ID，用于多轮对话续传（可选）

        Returns:
            dict: {
                "message": str,    # AI 回复内容
                "thread_id": str,  # 当前会话线程 ID
            }
        """
        # 第一步：确定线程 ID
        # 如果提供了 thread_id，说明是续传（多轮对话）
        # 否则创建新线程
        if not thread_id:
            thread_id = f"user_{user_id}:{uuid.uuid4()}"

        try:
            # 第二步：导入并构建 LangGraph
            # 延迟导入（在函数内 import）避免循环依赖和启动时的 import 开销
            # WHY：graph.py 可能依赖 services 模块，延迟导入打破循环
            from app.graph.graph import build_default_graph
            from app.graph.agents.classifier import UserContext

            # 构建 StateGraph（多智能体协作图）
            graph = build_default_graph()

            # 创建用户上下文（传递用户身份到 Agent 执行环境）
            context = UserContext(id=user_id, username=username, passenger_id=passenger_id)

            # 配置 LangGraph 运行参数
            # thread_id：用于 checkpoint 持久化对话状态
            # user_context：注入到 Agent 的用户信息（Agent 通过 context 读取）
            config = {"configurable": {"thread_id": thread_id, "user_context": context}}

            # 第三步：分支执行
            if user_input.strip().lower() == "y":
                # "y" = 用户确认执行（针对 interrupt 场景）
                # 不传入新消息，让图从上次中断处继续执行
                events = graph.stream(None, config, stream_mode="values")
            else:
                # 普通用户输入：包装为 LangChain 消息格式
                # ("user", text) 表示来自用户的消息
                events = graph.stream({"messages": [("user", user_input)]}, config, stream_mode="values")

            # 第四步：提取最终回复
            result = ""
            for event in events:
                # 每个 event 包含完整的状态快照（因为 stream_mode="values"）
                messages = event.get("messages", [])
                if messages:
                    # 取最后一条消息（最新的回复）
                    msg = messages[-1] if isinstance(messages, list) else messages
                    if hasattr(msg, "content") and msg.content:
                        result = msg.content

            # 第五步：处理空结果（等待用户确认的场景）
            if not result:
                # 检查图是否处于等待用户输入的状态
                current = graph.get_state(config)
                if current.next:
                    # 图还有待执行的节点，说明在等待用户确认
                    # 返回提示信息引导用户
                    result = "AI助手即将执行操作。是否批准？输入'y'继续。"

            return {"message": result or "已处理", "thread_id": thread_id}

        except Exception as e:
            # 全局异常兜底
            # 记录完整堆栈以便排查
            log.exception("Graph execution failed")
            # 返回截断的错误消息（最多 100 字符）
            # WHY：防止 LLM API 错误消息中包含敏感信息
            return {"message": f"服务处理中: {str(e)[:100]}", "thread_id": thread_id}
