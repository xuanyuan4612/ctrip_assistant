"""用户管理端点"""
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
    return UserService.get_all(session, skip=skip, limit=limit)


@router.get("/users/{user_id}", response_model=UserResponseSchema)
def get_user(user_id: int, session: Session = Depends(get_db)):
    user = UserService.get_by_id(session, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")
    return user


@router.patch("/users/{user_id}", response_model=UserResponseSchema)
def update_user(user_id: int, obj_in: UserUpdateSchema, session: Session = Depends(get_db)):
    user = UserService.update(session, user_id, obj_in)
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")
    return user


@router.delete("/users")
def delete_users(ids: List[int], session: Session = Depends(get_db)):
    UserService.deletes(session, ids)
    return {"message": f"已删除 {len(ids)} 个用户"}
