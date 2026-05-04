# -*- coding: utf-8 -*-
"""
认证端点：登录 / 注册 / 令牌刷新 / 登出

提供用户认证相关的 REST API 端点，包括：
  - POST /auth/register：用户注册（创建账号 + 返回 JWT 令牌）
  - POST /auth/login：用户登录（验证密码 + 返回 JWT 令牌）
  - POST /auth/token：OAuth2 表单模式登录（兼容 Swagger UI）
  - POST /auth/logout：用户登出（当前为无操作，未来可加入令牌黑名单）

设计说明：
  - 注册和登录都在白名单中，无需 JWT 令牌
  - 登录同时返回 access_token，前端存储在 localStorage 或 Cookie 中
  - /auth/token 端点遵循 OAuth2 Password Flow，使 Swagger UI 的
    "Authorize" 按钮可以正常工作
  - WHY：兼容 OAuth2 规范意味着可以使用任意 OpenAPI 客户端自动处理认证
"""
import logging

from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from starlette import status

from app.schemas.user import UserCreateSchema, UserLoginSchema, UserLoginResponseSchema
from app.services.auth_service import AuthService
from app.api.deps import get_db

router = APIRouter()
log = logging.getLogger("app.api.auth")


@router.post("/auth/register", response_model=UserLoginResponseSchema)
def register(obj_in: UserCreateSchema, session: Session = Depends(get_db)):
    """
    用户注册

    创建新用户账号并返回 JWT 令牌，让用户可以立即开始使用，无需额外登录步骤。

    业务逻辑（委托给 AuthService）：
      1. 检查用户名是否已存在
      2. 对密码进行 bcrypt 哈希
      3. 将用户信息存入数据库
      4. 生成 JWT access_token
      5. 返回用户信息和令牌

    Args:
        obj_in: 用户注册信息（用户名、密码、手机号、真实姓名）
        session: SQLAlchemy 数据库会话（依赖注入）

    Returns:
        UserLoginResponseSchema: 包含用户信息 + JWT 令牌

    异常：
        401 AuthenticationError - 用户名已被注册
    """
    return AuthService.register(session, obj_in)


@router.post("/auth/login", response_model=UserLoginResponseSchema)
def login(obj_in: UserLoginSchema, session: Session = Depends(get_db)):
    """
    用户登录

    验证用户凭证并返回 JWT 令牌。

    业务逻辑（委托给 AuthService）：
      1. 根据用户名查找用户
      2. 使用 bcrypt 验证密码
      3. 生成 JWT access_token
      4. 返回用户信息和令牌

    Args:
        obj_in: 用户登录信息（用户名、密码）
        session: SQLAlchemy 数据库会话（依赖注入）

    Returns:
        UserLoginResponseSchema: 包含用户信息 + JWT 令牌

    异常：
        401 AuthenticationError - 用户名或密码错误（使用模糊提示防枚举攻击）
    """
    return AuthService.login(session, obj_in)


@router.post("/auth/token")
def token(form_data: OAuth2PasswordRequestForm = Depends(), session: Session = Depends(get_db)):
    """
    OAuth2 令牌端点（兼容 Swagger UI 的 Authorize 功能）

    这是 Swagger UI 自动调用的端点。当用户在 Swagger 页面点击
    "Authorize" 并输入用户名密码时，Swagger 会发送表单格式的请求到此端点。

    与 /auth/login 的区别：
      - 接受 OAuth2PasswordRequestForm（表单格式）而非 JSON
      - 返回标准的 OAuth2 token 响应格式（含 token_type）
      - WHY：让 Swagger UI 可以自动在后续请求中附加 Authorization 头

    Args:
        form_data: OAuth2 表单（username, password 字段）
        session: SQLAlchemy 数据库会话（依赖注入）

    Returns:
        {"access_token": "...", "token_type": "bearer"}
    """
    # 将表单数据转换为与 login 端点相同的结构
    login_data = UserLoginSchema(username=form_data.username, password=form_data.password)
    result = AuthService.login(session, login_data)
    return {"access_token": result["token"], "token_type": "bearer"}


@router.post("/auth/logout")
def logout():
    """
    用户登出

    当前实现为无操作（仅返回成功消息），因为 JWT 是无状态的，
    服务端不维护会话状态。

    未来改进：
      - 维护令牌黑名单（Redis），使登出的令牌立即失效
      - 结合 refresh_token 的吊销机制

    Returns:
        {"message": "已登出"}
    """
    return {"message": "已登出"}
