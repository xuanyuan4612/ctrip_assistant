# -*- coding: utf-8 -*-
"""
用户管理端点

提供用户的 CRUD（增删改查）操作 API。
这些端点都需要 JWT 认证（不在白名单中）。

端点列表：
  - GET    /users         - 用户列表（分页）
  - GET    /users/{id}    - 用户详情（单个）
  - PATCH  /users/{id}    - 更新用户信息
  - DELETE /users         - 批量删除用户

设计说明：
  - 查询参数 skip/limit 实现简单分页，避免一次返回过多数据
  - 修改和查询单个用户使用路径参数 {user_id}
  - 批量删除使用请求体传递 ID 列表（DELETE with body）
  - WHY：DELETE 带 body 虽不常见，但比逐个删除减少网络请求次数
"""
from typing import List

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from starlette import status

from app.schemas.user import UserResponseSchema, UserUpdateSchema
from app.services.user_service import UserService
from app.api.deps import get_db, get_current_user_id

router = APIRouter()


@router.get("/users", response_model=List[UserResponseSchema])
def list_users(skip: int = 0, limit: int = 100, session: Session = Depends(get_db)):
    """
    获取用户列表（分页）

    Args:
        skip: 跳过的记录数（用于分页偏移，默认 0）
        limit: 每页记录数（默认 100，最大应在前端限制）
        session: 数据库会话（依赖注入）

    Returns:
        用户列表，每个元素包含 id、username、phone、real_name 等字段
    """
    return UserService.get_all(session, skip=skip, limit=limit)


@router.get("/users/{user_id}", response_model=UserResponseSchema)
def get_user(user_id: int, session: Session = Depends(get_db)):
    """
    获取单个用户详情

    Args:
        user_id: 用户 ID（路径参数）
        session: 数据库会话（依赖注入）

    Returns:
        用户详细信息

    Raises:
        HTTPException 404: 用户不存在
    """
    user = UserService.get_by_id(session, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")
    return user


@router.patch("/users/{user_id}", response_model=UserResponseSchema)
def update_user(user_id: int, obj_in: UserUpdateSchema, session: Session = Depends(get_db)):
    """
    更新用户信息

    支持部分更新（PATCH 而非 PUT），只传递需要修改的字段即可。

    Args:
        user_id: 要更新的用户 ID
        obj_in: 包含要更新的字段（可选字段：phone, real_name, is_active）
        session: 数据库会话（依赖注入）

    Returns:
        更新后的用户信息

    Raises:
        HTTPException 404: 用户不存在
    """
    user = UserService.update(session, user_id, obj_in)
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")
    return user


@router.delete("/users")
def delete_users(ids: List[int], session: Session = Depends(get_db)):
    """
    批量删除用户

    一次请求中删除多个用户，减少网络往返。

    为什么使用请求体传递 ID 列表而非路径参数：
      - DELETE /users?id=1&id=2&id=3 方式 URL 长度受限
      - 从请求体读取 ID 列表更清晰，支持大量 ID

    Args:
        ids: 要删除的用户 ID 列表（请求体 JSON 数组）
        session: 数据库会话（依赖注入）

    Returns:
        {"message": "已删除 N 个用户"}
    """
    UserService.deletes(session, ids)
    return {"message": f"已删除 {len(ids)} 个用户"}
