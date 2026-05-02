"""JWT 认证中间件"""
import logging
import re

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse
from jose import jwt, ExpiredSignatureError

from app.core.config import settings

log = logging.getLogger("app.middleware.auth")


class AuthMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        path = request.url.path

        # 白名单检查
        for pattern in settings.AUTH_WHITELIST:
            if re.fullmatch(pattern, path):
                return await call_next(request)

        # Token 验证
        authorization = request.headers.get("Authorization", "")
        if not authorization.startswith("Bearer "):
            return JSONResponse(
                {"detail": "缺少认证令牌"}, status_code=401,
                headers={"WWW-Authenticate": "Bearer"},
            )

        token = authorization.split(" ", 1)[1]
        try:
            payload = jwt.decode(
                token,
                settings.JWT_SECRET_KEY.get_secret_value(),
                algorithms=[settings.JWT_ALGORITHM],
            )
            subject = payload.get("sub", "")
            request.state.username = subject
            return await call_next(request)
        except ExpiredSignatureError:
            return JSONResponse(
                {"detail": "令牌已过期，请重新登录"}, status_code=401,
                headers={"WWW-Authenticate": "Bearer"},
            )
        except Exception as e:
            log.warning(f"Token validation failed: {e}")
            return JSONResponse(
                {"detail": "无效的认证令牌"}, status_code=401,
                headers={"WWW-Authenticate": "Bearer"},
            )
