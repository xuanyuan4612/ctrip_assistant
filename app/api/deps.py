"""依赖注入"""
from typing import Generator

from fastapi import Request
from sqlalchemy.orm import Session

from db import sm


def get_db(request: Request) -> Generator[Session, None, None]:
    """SQLAlchemy session 依赖注入"""
    try:
        session = sm()
        yield session
    finally:
        session.close()


def get_current_user_id(request: Request) -> int:
    """从 JWT 中间件设置的 request.state 获取当前用户 ID"""
    raw = getattr(request.state, "username", "")
    if ":" in raw:
        return int(raw.split(":", 1)[0])
    return 0
