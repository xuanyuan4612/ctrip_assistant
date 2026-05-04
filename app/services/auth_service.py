# -*- coding: utf-8 -*-
"""
认证服务：用户注册与登录的业务逻辑

本模块封装了用户认证的核心业务逻辑，包括注册和登录两个关键流程。
所有的数据库操作通过 UserRepository 完成，密码处理通过 security 模块。

设计模式：服务层（Service Layer）
  - 将业务逻辑从 API 端点中抽离，保持端点代码简洁
  - 服务方法为类方法（@classmethod），方便直接调用，无需实例化
  - 依赖倒置：服务层依赖仓库层接口，而非直接操作数据库

注册流程：
  1. 检查用户名唯一性 → 重复则抛出 AuthenticationError
  2. bcrypt 哈希密码（明文永不入库）
  3. 创建用户记录
  4. 生成 JWT access_token
  5. 返回用户信息和令牌

登录流程：
  1. 根据用户名查找用户 → 不存在则抛出模糊错误
  2. bcrypt 验证密码 → 错误则抛出相同错误（防枚举攻击）
  3. 生成 JWT access_token（sub = "{user_id}:{username}"）
  4. 返回用户信息和令牌

安全设计：
  - 登录失败统一返回"用户名或密码错误"，不区分"用户名不存在"和"密码错误"
  - WHY：防止攻击者通过错误提示枚举已注册的用户名
"""
import logging

from sqlalchemy.orm import Session

from app.core.security import get_hashed_password, verify_password, create_access_token
from app.core.exceptions import AuthenticationError
from app.schemas.user import UserCreateSchema, UserLoginSchema
from app.db.repositories.user import UserRepository

log = logging.getLogger("app.services.auth")


class AuthService:
    """
    认证服务类

    提供用户注册和登录的业务逻辑处理。
    所有方法均为类方法，可直接调用 AuthService.register(...) 无需实例化。

    为什么使用类方法而非普通方法：
      - 服务类不需要维护内部状态，所有操作通过参数传递
      - 简化调用方式，避免在依赖注入中传递服务实例
    """

    # 共享的用户仓库实例
    # WHY：UserRepository 也是无状态的，可以复用同一个实例
    repo = UserRepository()

    @classmethod
    def register(cls, session: Session, obj_in: UserCreateSchema) -> dict:
        """
        用户注册

        完整流程：
          1. 唯一性检查：查询用户名是否已被占用
             - 已存在：抛出 AuthenticationError（使用统一的"认证失败"语义）
          2. 密码处理：使用 bcrypt 对明文密码进行加盐哈希
             - 哈希后的密码存储到数据库，原始密码不保留
          3. 数据持久化：调用 UserRepository 创建用户记录
          4. 令牌生成：使用 "{user.id}:{user.username}" 作为 JWT subject
             - subject 格式允许一次解码同时获取用户 ID 和用户名
          5. 结果返回：包含用户基本信息 + JWT 令牌

        Args:
            session: SQLAlchemy 数据库会话
            obj_in: 用户注册信息（username, password, phone, real_name）

        Returns:
            dict: {
                "id": int,           # 新创建的用户 ID
                "username": str,     # 用户名
                "token": str,        # JWT access_token
                "phone": str,        # 手机号
                "real_name": str,    # 真实姓名
            }

        Raises:
            AuthenticationError: 用户名已被注册
        """
        # 第一步：唯一性检查
        existing = cls.repo.get_by_username(session, obj_in.username)
        if existing:
            # WHY：使用"用户名已存在"而非"用户名已被注册"，
            # 后续可能扩展为"该用户名不可用"
            raise AuthenticationError("用户名已存在")

        # 第二步：密码哈希（不可逆）
        # 将明文密码替换为 bcrypt 哈希值
        obj_in.password = get_hashed_password(obj_in.password)

        # 第三步：创建用户
        user = cls.repo.create(session, obj_in)

        # 第四步：生成 JWT 令牌
        # subject 格式："{user_id}:{username}"
        # 解码时可通过 ":" 分割同时获取两个值
        token = create_access_token(f"{user.id}:{user.username}")

        # 第五步：返回结果
        return {
            "id": user.id,
            "username": user.username,
            "token": token,
            "phone": user.phone,
            "real_name": user.real_name,
        }

    @classmethod
    def login(cls, session: Session, obj_in: UserLoginSchema) -> dict:
        """
        用户登录

        完整流程：
          1. 用户查找：根据用户名查询用户记录
             - 未找到：抛出模糊的"用户名或密码错误"异常
          2. 密码验证：使用 bcrypt 验证提交的密码是否匹配存储的哈希
             - 不匹配：抛出与第一步相同的异常消息
          3. 令牌生成：创建新的 JWT access_token
          4. 结果返回：包含用户基本信息 + JWT 令牌

        安全设计：
          - 用户名不存在和密码错误返回相同的错误消息
          - WHY：防止攻击者通过枚举用户名来发现已注册账号
          - 可以考虑后续增加登录失败次数限制（在中间件层实现）

        Args:
            session: SQLAlchemy 数据库会话
            obj_in: 用户登录信息（username, password）

        Returns:
            dict: {
                "id": int,
                "username": str,
                "token": str,
                "phone": str,
                "real_name": str,
            }

        Raises:
            AuthenticationError: 用户名或密码错误（统一错误消息）
        """
        # 第一步：查找用户
        user = cls.repo.get_by_username(session, obj_in.username)
        if not user:
            # 故意使用与密码错误相同的消息
            raise AuthenticationError("用户名或密码错误")

        # 第二步：验证密码
        # verify_password 内部从 user.password 提取盐值，
        # 对 obj_in.password 加盐哈希后比较
        if not verify_password(obj_in.password, user.password):
            # 同样使用模糊消息
            raise AuthenticationError("用户名或密码错误")

        # 第三步：生成 JWT 令牌
        token = create_access_token(f"{user.id}:{user.username}")

        # 第四步：返回结果
        return {
            "id": user.id,
            "username": user.username,
            "token": token,
            "phone": user.phone,
            "real_name": user.real_name,
        }
