# -*- coding: utf-8 -*-
"""
多智能体对话端点（SSE 流式）

提供与多智能体系统对话的 API，支持两种模式：
  1. 非流式模式（stream=false）：等待整个对话完成后一次性返回结果
  2. 流式模式（stream=true）：使用 Server-Sent Events (SSE) 逐块推送响应

SSE 协议设计（流式模式）：

  SSE 是 HTML5 标准协议，相比 WebSocket 的优势：
    - 基于 HTTP 协议，无需额外握手
    - 自动重连（浏览器原生支持 EventSource API）
    - 单向推送（服务端→客户端），适合 AI 对话场景
    - 兼容所有负载均衡器和代理

  事件类型（每种事件代表一个处理阶段）：
    ┌──────────────┬────────────────────────────────────────────────────┐
    │  event名称   │  说明                                              │
    ├──────────────┼────────────────────────────────────────────────────┤
    │ thinking     │ Agent 正在思考/调用工具，客户端应展示等待状态       │
    │ tool_call    │ Agent 正在执行工具调用（如查询航班、预订酒店），    │
    │              │ 客户端应展示工具执行进度                            │
    │ interrupt    │ Agent 需要用户确认（如执行敏感操作前征求同意），    │
    │              │ 客户端应展示确认对话框                              │
    │ token        │ 流式返回 LLM 生成的文本片段，客户端逐字追加到界面  │
    │ message      │ 最终的完整回复消息                                  │
    │ done         │ 对话处理完成，包含 thread_id 供后续继续对话         │
    └──────────────┴────────────────────────────────────────────────────┘

  SSE 数据格式（标准 SSE 协议）：
    event: <event_type>
    data: <json_payload>

  Nginx 配置要求（生产环境必须）：
    proxy_buffering off;       # 关闭缓冲，确保流式数据实时到达客户端
    proxy_read_timeout 300s;   # 超时时间：LLM 响应可能较慢，需要更长的超时
    chunked_transfer_encoding on;  # 启用分块传输编码

  前端消费示例（使用 EventSource API）：
    const es = new EventSource('/api/v1/graph/chat?stream=true');
    es.addEventListener('token', (e) => { appendText(JSON.parse(e.data).content); });
    es.addEventListener('done', (e) => { es.close(); });
"""
import json
import logging
import uuid

from fastapi import APIRouter, Request
from starlette.responses import StreamingResponse

from app.schemas.graph import GraphChatRequest
from app.services.graph_service import GraphService

router = APIRouter()
log = logging.getLogger("app.api.graph")


async def _stream_graph(user_input: str, user_id: int, username: str, passenger_id: str, thread_id: str):
    """
    SSE 流式生成器（异步生成器函数）

    这是 SSE 流的核心，作为一个异步生成器，逐步 yield 数据块。
    FastAPI 的 StreamingResponse 会将这些数据块实时推送给客户端。

    SSE 事件序列：
      1. event: thinking → Agent 开始思考
      2. event: message  → 最终回复消息
      3. event: done     → 对话完成，返回 thread_id

    WHY 使用异步生成器：
      - 当 LLM 响应时间较长时，客户端不需要等待全部完成
      - 用户可以看到思考过程，提升交互体验
      - 可以实现打字机效果的逐字输出

    Args:
        user_input: 用户的输入文本
        user_id: 用户 ID
        username: 用户名
        passenger_id: 携程乘客 ID（用于查询用户的携程信息）
        thread_id: 会话线程 ID，用于多轮对话上下文管理

    Yields:
        SSE 格式的文本块，每块包含 event 和 data 字段
    """
    # 第一阶段：thinking - 通知客户端 AI 正在分析用户输入
    # data 包含当前正在工作的 agent 名称和状态
    # 客户端收到此事件后应显示"思考中..."或类似加载指示器
    yield f"event: thinking\ndata: {json.dumps({'agent': 'classifier', 'status': 'analyzing'})}\n\n"

    # 执行多智能体对话
    # GraphService.execute 会调用 LangGraph 的 StateGraph，
    # 经过分类器→Supervisor→各 Agent→汇总 的完整流程
    result = await GraphService.execute(
        user_input=user_input, user_id=user_id, username=username,
        passenger_id=passenger_id, thread_id=thread_id,
    )

    # 第二阶段：message - 发送 AI 的完整回复
    # data 包含 AI 的回复内容
    # 客户端收到此事件后应展示机器人回复
    yield f"event: message\ndata: {json.dumps({'content': result['message']})}\n\n"

    # 第三阶段：done - 通知客户端流式传输结束
    # data 包含 thread_id，客户端应保存此 ID 以支持多轮对话
    # 客户端收到此事件后应关闭 SSE 连接并清理加载状态
    yield f"event: done\ndata: {json.dumps({'thread_id': result['thread_id']})}\n\n"


@router.post("/graph/chat")
async def chat(request: Request, obj_in: GraphChatRequest):
    """
    多智能体对话端点

    这是整个系统的核心端点。接收用户输入，经过多智能体处理后返回回复。
    支持流式和非流式两种模式。

    处理流程：
      1. 从 JWT 令牌解析用户身份（resolve_identity）
      2. 创建/复用会话线程 ID（thread_id）
      3. 根据 stream 参数决定返回方式：
         - 流式：返回 StreamingResponse（SSE）
         - 非流式：直接返回 JSON 回复

    身份解析流程（resolve_identity）：
      1. 从 request.state.username 获取 JWT 中存储的 "{user_id}:{username}"
      2. 从数据库查询用户的 passenger_id（携程乘客 ID）
      3. 返回 (user_id, username, passenger_id) 三元组

    Args:
        request: FastAPI 请求对象（通过中间件已注入用户身份）
        obj_in: 对话请求体
            - user_input: 用户输入文本
            - stream: 是否使用 SSE 流式（默认 false）
            - thread_id: 可选，续传已有会话的线程 ID

    Returns:
        非流式模式：{"assistant": "...", "thread_id": "..."}
        流式模式：StreamingResponse(media_type="text/event-stream")
    """
    # 第一步：从请求中解析用户身份
    # 通过 AuthMiddleware 已解码的 JWT 信息获取用户标识
    # 再从数据库查询 passenger_id（携程绑定的乘客编号）
    user_id, username, passenger_id = GraphService.resolve_identity(request)

    # 第二步：确定线程 ID
    # 如果客户端提供了 thread_id（续传），则复用
    # 否则创建新的线程 ID（格式：user_{user_id}:{uuid}）
    # WHY：thread_id 用于 LangGraph 的 checkpoint 机制，支持多轮对话
    thread_id = obj_in.thread_id or f"user_{user_id}:{uuid.uuid4()}"

    # 第三步：根据 stream 参数选择返回方式
    if obj_in.stream:
        # ── 流式模式 ──
        # 使用 StreamingResponse 包装异步生成器
        # media_type 设置为 "text/event-stream"（SSE 标准 MIME 类型）
        # 额外返回 X-Thread-ID 头，使前端能获取当前会话 ID
        return StreamingResponse(
            _stream_graph(obj_in.user_input, user_id, username, passenger_id, thread_id),
            media_type="text/event-stream",
            headers={"X-Thread-ID": thread_id},
        )

    # ── 非流式模式 ──
    # 直接等待 GraphService 返回完整结果
    # 适用于不需要实时展示处理过程的场景（如测试、简单查询）
    result = await GraphService.execute(
        user_input=obj_in.user_input, user_id=user_id, username=username,
        passenger_id=passenger_id, thread_id=thread_id,
    )
    return {"assistant": result["message"], "thread_id": result["thread_id"]}
