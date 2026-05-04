# -*- coding: utf-8 -*-
"""
依赖注入（FastAPI Dependencies）

提供可在路由处理函数中通过 Depends() 注入的公共依赖。

FastAPI 依赖注入系统：
  - 自动管理依赖的生命周期
  - 支持嵌套依赖（依赖可以依赖其他依赖）
  - 在 OpenAPI 文档中自动生成参数说明

本模块提供的依赖：
  1. get_db: 提供 SQLAlchemy 数据库会话（每个请求独立，用完自动关闭）
  2. get_current_user_id: 从 JWT 中间件设置的 request.state 获取当前用户 ID
"""
from typing import Generator

from fastapi import Request
from sqlalchemy.orm import Session

from db import sm


def get_db(request: Request) -> Generator[Session, None, None]:
    """
    SQLAlchemy 数据库会话依赖注入

    每个 HTTP 请求独立创建一个数据库会话，在请求结束后自动关闭。
    这是 FastAPI 依赖注入的典型用法：在函数中 yield 资源，
    try/finally 确保资源被释放。

    为什么使用 Generator 而非直接返回 Session：
      - yield 之前的代码在请求开始时执行（创建会话）
      - yield 之后的代码在请求结束时执行（关闭会话）
      - 这确保了即使发生异常，会话也会被正确关闭

    依赖链：
      HTTP 请求 → get_db (创建 Session) → 路由处理 (使用 Session) → 关闭 Session

    Args:
        request: FastAPI 请求对象（虽然未直接使用，但 FastAPI 依赖注入
                 需要 Request 参数来确定作用域）

    Yields:
        SQLAlchemy Session 实例
    """
    try:
        # 创建新的数据库会话
        # sm 是 SQLAlchemy sessionmaker，在 db/__init__.py 中初始化
        session = sm()
        yield session
    finally:
        # 确保会话被关闭，归还连接到连接池
        # 如果不关闭，连接池会耗尽导致后续请求无法获取数据库连接
        session.close()


def get_current_user_id(request: Request) -> int:
    """
    从 JWT 中间件提取当前用户 ID

    依赖 AuthMiddleware 已经执行并将用户标识写入 request.state.username。
    用户标识格式为 "{user_id}:{username}"，例如 "42:zhangsan"。

    为什么不直接从路由参数获取：
      - 每个需要用户信息的端点都需要重复写解析逻辑
      - 依赖注入统一处理，减少重复代码

    Args:
        request: FastAPI 请求对象（已由 AuthMiddleware 注入用户信息）

    Returns:
        当前用户的数字 ID，解析失败返回 0

    使用示例：
        @router.get("/profile")
        def get_profile(user_id: int = Depends(get_current_user_id)):
            ...
    """
    # 从 request.state 获取用户名标识
    # request.state.username 是 AuthMiddleware 在 JWT 解码成功后设置的
    raw = getattr(request.state, "username", "")
    # 解析 "{user_id}:{username}" 格式
    if ":" in raw:
        return int(raw.split(":", 1)[0])
    # 如果未正常解析（如 JWT 格式异常），返回 0 表示匿名/无效用户
    return 0
