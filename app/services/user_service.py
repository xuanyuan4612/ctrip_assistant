# -*- coding: utf-8 -*-
"""
用户服务：用户 CRUD 操作的业务逻辑委托层

本模块是 API 端点和数据仓库之间的中间层，负责：
  1. 将 API 层的调用转发到 UserRepository
  2. 在需要时添加业务逻辑（如数据校验、权限检查）
  3. 保持 API 端点和仓库层的职责分离

设计模式：服务层（Service Layer）/ 委托模式（Delegation）
  - 当前实现主要是对 UserRepository 的简单委托
  - 未来可在此添加业务逻辑而不影响 API 端点和仓库层
  - 例如：创建用户时发送欢迎通知、删除用户时级联删除相关数据
"""
from typing import List, Optional

from sqlalchemy.orm import Session

from app.schemas.user import UserCreateSchema, UserUpdateSchema
from app.db.repositories.user import UserRepository


class UserService:
    """
    用户服务类

    封装用户相关的业务操作，对外提供统一的接口。
    所有方法均为类方法，直接调用 UserService.method()。

    方法概览：
      - get_all：分页获取用户列表
      - get_by_id：获取单个用户
      - create：创建用户（已在 AuthService.register 中使用）
      - update：更新用户信息
      - deletes：批量删除用户
    """

    # 共享的用户仓库实例
    repo = UserRepository()

    @classmethod
    def get_all(cls, session: Session, skip: int = 0, limit: int = 100) -> List:
        """
        分页获取用户列表

        委托给 UserRepository.get_all，支持偏移分页。

        Args:
            session: 数据库会话
            skip: 跳过的记录数（默认 0）
            limit: 每页记录数（默认 100）

        Returns:
            用户对象列表
        """
        return cls.repo.get_all(session, skip=skip, limit=limit)

    @classmethod
    def get_by_id(cls, session: Session, user_id: int):
        """
        根据 ID 获取单个用户

        Args:
            session: 数据库会话
            user_id: 用户 ID

        Returns:
            用户对象，不存在则返回 None
        """
        return cls.repo.get_by_id(session, user_id)

    @classmethod
    def create(cls, session: Session, obj_in: UserCreateSchema):
        """
        创建新用户

        注意：通常在 AuthService.register 中使用，
        UserService.create 作为通用接口保留。

        Args:
            session: 数据库会话
            obj_in: 用户创建信息

        Returns:
            新创建的用户对象
        """
        return cls.repo.create(session, obj_in)

    @classmethod
    def update(cls, session: Session, user_id: int, obj_in: UserUpdateSchema):
        """
        更新用户信息

        支持部分更新（仅修改提供的字段）。

        Args:
            session: 数据库会话
            user_id: 要更新的用户 ID
            obj_in: 包含要更新的字段

        Returns:
            更新后的用户对象，用户不存在则返回 None
        """
        return cls.repo.update(session, user_id, obj_in)

    @classmethod
    def deletes(cls, session: Session, ids: List[int]):
        """
        批量删除用户

        一次性删除多个用户，比逐个删除效率更高。

        Args:
            session: 数据库会话
            ids: 要删除的用户 ID 列表
        """
        cls.repo.deletes(session, ids)
