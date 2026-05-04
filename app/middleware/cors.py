# -*- coding: utf-8 -*-
"""
CORS 中间件配置

配置跨域资源共享（Cross-Origin Resource Sharing），允许前端页面
从不同域名/端口访问后端 API。

配置项：
  - allow_origins：允许的来源列表（在 settings.CORS_ORIGINS 中配置）
  - allow_credentials：允许携带 Cookie（前后端分离时需要）
  - allow_methods：允许的 HTTP 方法（* 表示全部）
  - allow_headers：允许的请求头（* 表示全部）

安全建议：
  生产环境应将 CORS_ORIGINS 设置为具体的前端域名，
  而非使用通配符，以防止跨站请求伪造（CSRF）攻击。
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings


def init_cors(app: FastAPI) -> None:
    """
    为 FastAPI 应用添加 CORS 中间件

    在 app 上注册 CORSMiddleware，允许前端跨域请求。
    调用位置在 main.py 的 create_app() 中，在 RequestIDMiddleware 之后、
    AuthMiddleware 之前注册。

    为什么单独提取为一个函数：
      - 保持 main.py 简洁
      - 方便未来扩展 CORS 配置逻辑（如动态读取允许源列表）

    Args:
        app: FastAPI 应用实例
    """
    app.add_middleware(
        CORSMiddleware,
        # 允许的来源：必须与前端实际部署地址匹配
        # 开发环境通常是 http://localhost:5173 或 http://localhost:8080
        allow_origins=settings.CORS_ORIGINS,
        # 允许跨域携带 Cookie（用于 session/cookie 认证场景）
        allow_credentials=True,
        # 允许所有 HTTP 方法（GET、POST、PUT、DELETE、OPTIONS 等）
        allow_methods=["*"],
        # 允许所有请求头（包括自定义的 Authorization、X-Request-ID 等）
        allow_headers=["*"],
    )
