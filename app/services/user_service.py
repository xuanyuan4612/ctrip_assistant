"""用户服务"""
from typing import List, Optional

from sqlalchemy.orm import Session

from app.schemas.user import UserCreateSchema, UserUpdateSchema
from app.db.repositories.user import UserRepository


class UserService:
    repo = UserRepository()

    @classmethod
    def get_all(cls, session: Session, skip: int = 0, limit: int = 100) -> List:
        return cls.repo.get_all(session, skip=skip, limit=limit)

    @classmethod
    def get_by_id(cls, session: Session, user_id: int):
        return cls.repo.get_by_id(session, user_id)

    @classmethod
    def create(cls, session: Session, obj_in: UserCreateSchema):
        return cls.repo.create(session, obj_in)

    @classmethod
    def update(cls, session: Session, user_id: int, obj_in: UserUpdateSchema):
        return cls.repo.update(session, user_id, obj_in)

    @classmethod
    def deletes(cls, session: Session, ids: List[int]):
        cls.repo.deletes(session, ids)
