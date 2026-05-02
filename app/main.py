"""FastAPI 应用工厂"""
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
    setup_logging()
    app.state.logger = __import__("logging").getLogger("app")
    app.state.logger.info(f"Starting {settings.APP_NAME}...")
    yield
    app.state.logger.info(f"Shutting down {settings.APP_NAME}...")


def create_app() -> FastAPI:
    app = FastAPI(
        title="携程 AI 助手",
        version="1.0.0",
        lifespan=lifespan,
    )

    # ── 中间件 (顺序重要) ──
    from app.middleware.cors import init_cors
    from app.middleware.auth import AuthMiddleware
    from app.middleware.request_id import RequestIDMiddleware

    app.add_middleware(RequestIDMiddleware)
    init_cors(app)
    app.add_middleware(AuthMiddleware)

    # ── 异常处理 ──
    @app.exception_handler(AppException)
    async def app_exception_handler(request: Request, exc: AppException):
        return JSONResponse(
            status_code=exc.status_code,
            content={"error": {"code": type(exc).__name__, "message": exc.detail}},
        )

    @app.exception_handler(HTTPException)
    async def http_exception_handler(request: Request, exc: HTTPException):
        return JSONResponse(status_code=exc.status_code, content={"detail": exc.detail})

    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(request: Request, exc: RequestValidationError):
        return JSONResponse(
            status_code=422,
            content={"error": {"code": "VALIDATION_ERROR", "message": str(exc), "errors": exc.errors()}},
        )

    @app.exception_handler(Exception)
    async def unhandled_exception_handler(request: Request, exc: Exception):
        app.state.logger.exception("Unhandled exception")
        return JSONResponse(
            status_code=500,
            content={"error": {"code": "INTERNAL_ERROR", "message": "服务器内部错误"}},
        )

    # ── 路由 ──
    from app.api.v1.router import v1_router
    app.include_router(v1_router, prefix="/api/v1")

    return app
