# -*- coding: utf-8 -*-
"""
FastAPI 应用工厂

负责创建和配置 FastAPI 应用实例，包括：
  1. 生命周期管理（lifespan）：启动时初始化日志，关闭时清理资源
  2. 中间件注册：RequestID → CORS → Auth（顺序严格，不可颠倒）
  3. 全局异常处理器：统一捕获业务异常和未预期错误
  4. 路由注册：挂载 v1 版 API 路由

中间件执行顺序说明：
  请求进入：RequestID → CORS → Auth → 路由处理
  响应返回：Auth → CORS → RequestID
  WHY：RequestID 在最外层确保所有日志都有追踪 ID；Auth 在内层
  可以访问 RequestID 中间件设置的 request.state
"""
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from starlette.exceptions import HTTPException
from fastapi.exceptions import RequestValidationError
from starlette.responses import JSONResponse
from starlette.requests import Request

from app.core.config import settings
from app.core.logging import setup_logging
from app.core.exceptions import AppException


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    应用生命周期管理器

    在应用启动和关闭时执行自定义逻辑。
    FastAPI 的 lifespan 替代了旧的 startup/shutdown 事件。

    启动时（yield 之前）：
      1. 初始化日志配置
      2. 在 app.state 存储全局可用的 logger 实例
      3. 记录应用启动日志

    关闭时（yield 之后）：
      1. 记录应用关闭日志
      2. 释放数据库连接池等资源（如有）

    WHY：使用 lifespan 而非 startup/shutdown 事件，因为它是
    FastAPI 推荐的现代方式，且类型安全。
    """
    # 初始化日志配置（必须在任何日志记录之前调用）
    setup_logging()
    # 将 logger 存入 app.state，方便全局访问
    app.state.logger = __import__("logging").getLogger("app")
    app.state.logger.info(f"Starting {settings.APP_NAME}...")
    yield  # 应用在此运行
    app.state.logger.info(f"Shutting down {settings.APP_NAME}...")


def create_app() -> FastAPI:
    """
    创建并配置 FastAPI 应用实例

    这是应用的入口点，由 uvicorn 调用（通过 main.py 或直接调用）。

    配置流程（顺序重要）：
      1. 创建 FastAPI 实例，设置标题和版本号
      2. 注册中间件（按处理顺序）：
         a. RequestIDMiddleware：为每个请求分配唯一 ID
         b. CORSMiddleware：处理跨域请求
         c. AuthMiddleware：JWT 认证（访问 request.state.request_id）
      3. 注册全局异常处理器
      4. 注册 API 路由

    Returns:
        配置完成的 FastAPI 应用实例
    """
    app = FastAPI(
        title="携程 AI 助手",
        version="1.0.0",
        lifespan=lifespan,
    )

    # ── 中间件（注册顺序 = 执行顺序，非常重要） ──
    #
    # 执行链（请求方向）：
    #   RequestID → CORS → Auth → [路由处理]
    # 执行链（响应方向）：
    #   [路由处理] → Auth → CORS → RequestID
    #
    # 为什么 RequestID 最先注册：
    #   确保即使认证失败，响应也有 X-Request-ID 头，方便追踪
    # 为什么 Auth 最后注册：
    #   需要访问前面中间件设置的状态（如 request.state.request_id）
    from app.middleware.cors import init_cors
    from app.middleware.auth import AuthMiddleware
    from app.middleware.request_id import RequestIDMiddleware

    # 第1层：请求追踪ID（最外层，包裹所有请求和响应）
    app.add_middleware(RequestIDMiddleware)
    # 第2层：跨域支持（处理 OPTIONS 预检请求）
    init_cors(app)
    # 第3层：JWT 认证（最内层，靠近路由处理）
    app.add_middleware(AuthMiddleware)

    # ── 全局异常处理器 ──
    #
    # 异常处理优先级：注册顺序逆序（最后注册的优先匹配）
    # 所以精确匹配的异常处理器应后注册
    #
    # 处理链：
    #   未处理异常 → HTTPException → AppException → RequestValidationError

    @app.exception_handler(AppException)
    async def app_exception_handler(request: Request, exc: AppException):
        """
        处理所有业务异常（继承自 AppException 的异常）

        返回格式：
        {
            "error": {
                "code": "AuthenticationError",  # 异常类名
                "message": "用户名或密码错误"     # 错误详情
            }
        }
        WHY：统一错误格式，前端可以按 code 做国际化或特定处理
        """
        return JSONResponse(
            status_code=exc.status_code,
            content={"error": {"code": type(exc).__name__, "message": exc.detail}},
        )

    @app.exception_handler(HTTPException)
    async def http_exception_handler(request: Request, exc: HTTPException):
        """
        处理标准 HTTP 异常（FastAPI 内置的 HTTPException）

        这是 AppException 的父类，但如果子类处理器已匹配则不会到达这里。
        这里处理那些直接抛出 HTTPException 而不是 AppException 的情况。

        返回格式：标准的 {"detail": "..."} 格式，保持与 FastAPI 默认一致
        """
        return JSONResponse(status_code=exc.status_code, content={"detail": exc.detail})

    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(request: Request, exc: RequestValidationError):
        """
        处理请求数据验证错误（Pydantic 校验失败）

        当请求体/路径参数/查询参数类型不匹配时触发。
        返回详细的字段级错误信息，方便前端定位问题。

        返回格式：
        {
            "error": {
                "code": "VALIDATION_ERROR",
                "message": "...",
                "errors": [...]  # Pydantic 详细错误列表
            }
        }
        WHY：Pydantic 的错误信息包含具体哪个字段验证失败，
        直接透传给前端可以精确定位问题
        """
        return JSONResponse(
            status_code=422,
            content={
                "error": {
                    "code": "VALIDATION_ERROR",
                    "message": str(exc),
                    "errors": exc.errors(),  # 字段级错误详情
                }
            },
        )

    @app.exception_handler(Exception)
    async def unhandled_exception_handler(request: Request, exc: Exception):
        """
        兜底异常处理器（最后一个防线）

        捕获所有未被上述处理器匹配的异常。
        记录完整堆栈日志，但返回给客户端的是脱敏后的通用消息。
        WHY：不暴露内部实现细节给客户端，防止信息泄露

        返回格式：
        {
            "error": {
                "code": "INTERNAL_ERROR",
                "message": "服务器内部错误"
            }
        }
        """
        app.state.logger.exception("Unhandled exception")
        return JSONResponse(
            status_code=500,
            content={"error": {"code": "INTERNAL_ERROR", "message": "服务器内部错误"}},
        )

    # ── 路由注册 ──
    # 所有 v1 版本的 API 端点都通过 router.py 聚合后挂载
    # 前缀 /api/v1，例如：/api/v1/health, /api/v1/auth/login
    from app.api.v1.router import v1_router
    app.include_router(v1_router, prefix="/api/v1")

    return app
