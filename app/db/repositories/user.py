"""用户 Repository"""
from typing import Optional, List

from sqlalchemy import select, text
from sqlalchemy.orm import Session

from app.schemas.user import UserCreateSchema, UserUpdateSchema
from app.db.models.user import UserModel


class UserRepository:
    model = UserModel

    def get_all(self, session: Session, skip: int = 0, limit: int = 100) -> List:
        stmt = select(self.model).offset(skip).limit(limit)
        return session.execute(stmt).scalars().all()

    def get_by_id(self, session: Session, pk: int) -> Optional:
        return session.get(self.model, pk)

    def get_by_username(self, session: Session, username: str) -> Optional:
        stmt = select(self.model).where(self.model.username == username)
        return session.execute(stmt).scalars().first()

    def get_by_username_raw(self, user_id: int):
        """仅获取 username 和 passenger_id (避免加载完整对象)"""
        return session.get(self.model, user_id) if (session := __import__("db").sm()) else None

    def create(self, session: Session, obj_in: UserCreateSchema):
        obj = self.model(**obj_in.model_dump())
        session.add(obj)
        session.commit()
        session.refresh(obj)
        return obj

    def update(self, session: Session, pk: int, obj_in: UserUpdateSchema) -> Optional:
        obj = self.get_by_id(session, pk)
        if not obj:
            return None
        update_data = obj_in.model_dump(exclude_unset=True)
        for key, val in update_data.items():
            setattr(obj, key, val)
        session.commit()
        session.refresh(obj)
        return obj

    def deletes(self, session: Session, ids: List[int]):
        stmt = text("DELETE FROM t_usermodel WHERE id IN :ids")
        session.execute(stmt, {"ids": tuple(ids)})
        session.commit()
