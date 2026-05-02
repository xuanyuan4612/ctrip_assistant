"""认证服务"""
import logging

from sqlalchemy.orm import Session

from app.core.security import get_hashed_password, verify_password, create_access_token
from app.core.exceptions import AuthenticationError
from app.schemas.user import UserCreateSchema, UserLoginSchema
from app.db.repositories.user import UserRepository

log = logging.getLogger("app.services.auth")


class AuthService:
    repo = UserRepository()

    @classmethod
    def register(cls, session: Session, obj_in: UserCreateSchema) -> dict:
        existing = cls.repo.get_by_username(session, obj_in.username)
        if existing:
            raise AuthenticationError("用户名已存在")

        obj_in.password = get_hashed_password(obj_in.password)
        user = cls.repo.create(session, obj_in)
        token = create_access_token(f"{user.id}:{user.username}")

        return {
            "id": user.id,
            "username": user.username,
            "token": token,
            "phone": user.phone,
            "real_name": user.real_name,
        }

    @classmethod
    def login(cls, session: Session, obj_in: UserLoginSchema) -> dict:
        user = cls.repo.get_by_username(session, obj_in.username)
        if not user:
            raise AuthenticationError("用户名或密码错误")

        if not verify_password(obj_in.password, user.password):
            raise AuthenticationError("用户名或密码错误")

        token = create_access_token(f"{user.id}:{user.username}")

        return {
            "id": user.id,
            "username": user.username,
            "token": token,
            "phone": user.phone,
            "real_name": user.real_name,
        }
