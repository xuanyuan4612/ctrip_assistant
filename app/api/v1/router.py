"""API v1 路由聚合"""
from fastapi import APIRouter

from app.api.v1.health import router as health_router
from app.api.v1.auth import router as auth_router
from app.api.v1.users import router as users_router
from app.api.v1.graph import router as graph_router

v1_router = APIRouter()
v1_router.include_router(health_router, tags=["系统"])
v1_router.include_router(auth_router, tags=["认证"])
v1_router.include_router(users_router, tags=["用户管理"])
v1_router.include_router(graph_router, tags=["多智能体对话"])
