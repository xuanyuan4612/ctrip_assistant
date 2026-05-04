# -*- coding: utf-8 -*-
"""
请求追踪 ID 中间件

为每个 HTTP 请求分配一个唯一标识符（UUID），并在整个请求处理链中传递。
这个 ID 会：
  1. 写入响应头 X-Request-ID，便于客户端追踪请求
  2. 存入 request.state.request_id，供日志记录使用
  3. 如果客户端提供了 X-Request-ID，则复用（支持链路追踪透传）

设计模式：请求追踪（Request Tracing）
  - 在微服务架构中，通过 Trace ID 串联多个服务的调用链
  - 即使单体应用，Trace ID 也能帮助快速关联日志和定位问题
  - WHY：没有 Trace ID 时，多并发请求的日志交织在一起难以区分
"""
import uuid

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request


class RequestIDMiddleware(BaseHTTPMiddleware):
    """
    请求追踪 ID 中间件

    为每个请求生成唯一标识，支持从上游服务透传 ID。

    执行时机：最早执行的中间件（在 main.py 中最先注册）
    确保即使在认证失败的情况下，响应中也包含 X-Request-ID，
    方便调试和日志追踪。

    使用方式：
      - 客户端传入：在请求头中添加 X-Request-ID
      - 服务端生成：未传入时自动生成 UUID
      - 日志使用：log.info("msg", extra={"request_id": request.state.request_id})
    """

    async def dispatch(self, request: Request, call_next):
        """
        为请求分配/透传追踪 ID

        流程：
          1. 检查请求头 X-Request-ID
          2. 有则复用（上游服务传入的 Trace ID）
          3. 无则生成新的 UUID v4
          4. 存入 request.state 供后续中间件和路由使用
          5. 在响应头中返回该 ID

        Args:
            request: 当前 HTTP 请求
            call_next: 下一个中间件

        Returns:
            HTTP 响应（包含 X-Request-ID 头）
        """
        # 从请求头获取或生成新的 UUID
        # WHY UUID v4：基于随机数，无需协调中心节点，适合分布式环境
        request_id = request.headers.get("X-Request-ID", str(uuid.uuid4()))
        # 存入 request.state，供日志记录器和业务代码使用
        request.state.request_id = request_id
        # 传递给下一个中间件/路由
        response = await call_next(request)
        # 在响应头中返回追踪 ID，方便客户端关联请求和响应
        response.headers["X-Request-ID"] = request_id
        return response
