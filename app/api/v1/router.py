# -*- coding: utf-8 -*-
"""
API v1 路由聚合器

将所有 v1 版本的子路由聚合到主路由器上，实现关注点分离。
每个子路由模块（health/auth/users/graph）各自管理自己的端点，
通过本文件统一挂载到主应用。

设计模式：路由组合（Route Composition）
  - 每个子模块独立定义 APIRouter，维护自己的端点
  - 本文件导入所有子模块的路由器，组合成 v1_router
  - 在 main.py 中将 v1_router 挂载到 /api/v1 前缀下
  - WHY：避免单个路由文件过于庞大，各模块职责清晰

路由层次：
  /api/v1
    ├── /health          → health_router
    ├── /auth/*          → auth_router
    ├── /users           → users_router
    └── /graph/*         → graph_router
"""
from fastapi import APIRouter

from app.api.v1.health import router as health_router  # 健康检查：无认证
from app.api.v1.auth import router as auth_router      # 认证相关：登录/注册/刷新/登出
from app.api.v1.users import router as users_router    # 用户管理：需要 JWT 认证
from app.api.v1.graph import router as graph_router    # 多智能体对话：需要 JWT 认证，支持 SSE 流式

# 创建 v1 版本的主路由器
v1_router = APIRouter()

# 按功能域挂载子路由，tags 用于 Swagger 文档分组
v1_router.include_router(health_router, tags=["系统"])          # 系统健康检查端点
v1_router.include_router(auth_router, tags=["认证"])            # 用户认证端点
v1_router.include_router(users_router, tags=["用户管理"])        # 用户 CRUD 端点
v1_router.include_router(graph_router, tags=["多智能体对话"])    # 多智能体对话端点（SSE 流式）
