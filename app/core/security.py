# -*- coding: utf-8 -*-
"""
安全模块：JWT 令牌生成/验证 + bcrypt 密码哈希

本模块负责：
  1. 用户密码的安全存储（bcrypt 哈希，不可逆）
  2. JWT 访问令牌和刷新令牌的生成与解码

设计原则：
  - 密码绝不存储明文：使用 bcrypt 加盐哈希，即使数据库泄露也无法还原密码
  - JWT 自包含：令牌包含用户标识和过期时间，服务端无需维护会话状态
  - 双令牌机制：短时效 access_token（30分钟）+ 长时效 refresh_token（7天）
  - WHY：无状态认证减少数据库查询，双令牌平衡安全与体验
"""
from datetime import datetime, timedelta

from jose import jwt
from passlib.context import CryptContext

from app.core.config import settings

# bcrypt 密码上下文
# schemes=["bcrypt"]：使用 bcrypt 哈希算法
# deprecated="auto"：自动处理旧哈希格式升级
# WHY：bcrypt 内置加盐且计算速度可调，抗彩虹表攻击
password_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def get_hashed_password(password: str) -> str:
    """
    对明文密码进行 bcrypt 哈希

    流程：
      1. passlib 自动生成随机盐值（salt）
      2. 使用 bcrypt 算法对 password + salt 进行多次迭代哈希
      3. 返回的哈希字符串包含算法标识、盐值和哈希结果

    Args:
        password: 用户注册时提交的明文密码

    Returns:
        包含盐值和哈希结果的字符串（格式：$<salt><hash>）
    """
    return password_context.hash(password)


def verify_password(password: str, hashed_pass: str) -> bool:
    """
    验证明文密码是否与哈希匹配

    流程：
      1. 从 hashed_pass 中提取盐值
      2. 对传入的 password + 盐值重新计算哈希
      3. 比较两个哈希是否一致

    Args:
        password: 用户登录时提交的明文密码
        hashed_pass: 数据库中存储的 bcrypt 哈希字符串

    Returns:
        True 如果密码匹配，False 否则
    """
    return password_context.verify(password, hashed_pass)


def create_access_token(subject: str) -> str:
    """
    生成 JWT 访问令牌（Access Token）

    载荷（Payload）包含：
      - sub（subject）：用户标识，格式为 "{user_id}:{username}"
      - exp（expiration）：过期时间，当前时间 + 配置的 ACCESS_TOKEN_EXPIRE_MINUTES
      - type：固定为 "access"，用于区分令牌类型

    WHY：短过期时间（30分钟）降低令牌泄露风险

    Args:
        subject: 令牌主体，格式 "{user_id}:{username}"

    Returns:
        JWT 编码后的令牌字符串
    """
    expires = datetime.utcnow() + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    return jwt.encode(
        {"sub": subject, "exp": expires, "type": "access"},
        settings.JWT_SECRET_KEY.get_secret_value(),
        algorithm=settings.JWT_ALGORITHM,
    )


def create_refresh_token(subject: str) -> str:
    """
    生成 JWT 刷新令牌（Refresh Token）

    与 access_token 的区别：
      - 过期时间更长（7天）
      - type 字段为 "refresh"
      - 用于在 access_token 过期后获取新的 access_token

    WHY：避免用户频繁登录，同时保持短时效 access_token 的安全性

    Args:
        subject: 令牌主体，格式 "{user_id}:{username}"

    Returns:
        JWT 编码后的刷新令牌字符串
    """
    expires = datetime.utcnow() + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
    return jwt.encode(
        {"sub": subject, "exp": expires, "type": "refresh"},
        settings.JWT_SECRET_KEY.get_secret_value(),
        algorithm=settings.JWT_ALGORITHM,
    )


def decode_token(token: str) -> dict:
    """
    解码并验证 JWT 令牌

    验证内容：
      1. 签名是否有效（使用 JWT_SECRET_KEY 验证 HMAC）
      2. 令牌是否过期（基于 exp 字段）
      3. 算法是否匹配（防止算法混淆攻击）

    异常：
      - ExpiredSignatureError：令牌已过期
      - JWTError：签名无效或被篡改

    Args:
        token: JWT 令牌字符串

    Returns:
        解码后的载荷字典，包含 sub, exp, type 等字段
    """
    return jwt.decode(
        token,
        settings.JWT_SECRET_KEY.get_secret_value(),
        algorithms=[settings.JWT_ALGORITHM],
    )
