# -*- coding: utf-8 -*-
"""
JWT 认证中间件

在请求到达路由处理之前进行 JWT 令牌验证。实现了白名单机制，
某些路径（登录、注册、健康检查）无需认证即可访问。

认证流程：
  1. 检查请求路径是否在白名单中 → 是则直接放行
  2. 从 Authorization 头提取 Bearer Token
  3. 解码并验证 JWT 签名和过期时间
  4. 验证通过：将用户信息存入 request.state，放行到下一中间件/路由
  5. 验证失败：返回 401 响应

设计决策：
  - 使用中间件而非装饰器：全局统一拦截，无需在每个路由上加 @requires_auth
  - 白名单使用正则匹配：灵活支持路径模式（如 /docs 匹配 /docs 和 /docs#/...）
  - WHY：中间件方式避免遗漏路由，白名单机制灵活控制免认证路径
"""
import logging
import re

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse
from jose import jwt, ExpiredSignatureError

from app.core.config import settings

log = logging.getLogger("app.middleware.auth")


class AuthMiddleware(BaseHTTPMiddleware):
    """
    JWT 认证中间件

    继承自 Starlette 的 BaseHTTPMiddleware，在请求处理链中插入认证逻辑。
    所有请求都会经过 dispatch 方法（除了被白名单匹配的路径）。

    工作流程：
      1. 白名单匹配：遍历 AUTH_WHITELIST，使用正则 fullmatch 检查
      2. Token 提取：从 "Authorization: Bearer <token>" 头中提取令牌
      3. 令牌解码：使用 jose.jwt.decode 验证签名和过期时间
      4. 身份注入：将解码后的 sub（用户标识）存入 request.state.username
      5. 异常处理：分别处理令牌缺失、过期、无效三种情况
    """

    async def dispatch(self, request: Request, call_next):
        """
        中间件核心处理方法

        Args:
            request: 当前 HTTP 请求对象
            call_next: 下一个中间件或路由处理函数

        Returns:
            如果认证通过，返回 call_next(request) 的结果
            如果认证失败，返回 401 JSON 响应
        """
        path = request.url.path

        # ── 第一步：白名单检查 ──
        # 遍历配置中的白名单路径列表，使用正则完整匹配
        # WHY：使用 re.fullmatch 而非简单的字符串比较，
        # 因为白名单路径在配置中不包含尾部斜杠等变体
        for pattern in settings.AUTH_WHITELIST:
            if re.fullmatch(pattern, path):
                # 白名单匹配：直接放行到下一中间件/路由
                return await call_next(request)

        # ── 第二步：提取 Authorization 头 ──
        # 标准格式："Bearer eyJhbGciOiJIUzI1NiIs..."
        authorization = request.headers.get("Authorization", "")
        if not authorization.startswith("Bearer "):
            # 缺少或格式错误的 Authorization 头
            # 返回 401 + WWW-Authenticate 头，引导客户端重新认证
            return JSONResponse(
                {"detail": "缺少认证令牌"}, status_code=401,
                headers={"WWW-Authenticate": "Bearer"},
            )

        # ── 第三步：解码并验证 JWT 令牌 ──
        # 从 "Bearer xxx" 中提取令牌部分
        token = authorization.split(" ", 1)[1]
        try:
            # 解码：验证签名（HMAC-SHA256）、过期时间（exp）、算法
            payload = jwt.decode(
                token,
                settings.JWT_SECRET_KEY.get_secret_value(),
                algorithms=[settings.JWT_ALGORITHM],
            )
            # 提取用户标识，格式为 "{user_id}:{username}"
            # 例如："42:zhangsan"
            subject = payload.get("sub", "")
            # 将用户信息存入 request.state
            # 后续路由和依赖注入可通过 request.state.username 获取
            request.state.username = subject
            # 放行到下一处理环节
            return await call_next(request)

        except ExpiredSignatureError:
            # 令牌已过期：返回提示信息，前端可据此尝试刷新令牌
            return JSONResponse(
                {"detail": "令牌已过期，请重新登录"}, status_code=401,
                headers={"WWW-Authenticate": "Bearer"},
            )
        except Exception as e:
            # 其他解码错误：签名无效、令牌被篡改等
            # 记录警告日志（非 ERROR 级别，因为可能是客户端错误）
            log.warning(f"Token validation failed: {e}")
            return JSONResponse(
                {"detail": "无效的认证令牌"}, status_code=401,
                headers={"WWW-Authenticate": "Bearer"},
            )
