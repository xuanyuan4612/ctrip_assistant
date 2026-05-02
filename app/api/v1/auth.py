"""认证端点 (登录/注册/刷新/登出)"""
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
    return AuthService.register(session, obj_in)


@router.post("/auth/login", response_model=UserLoginResponseSchema)
def login(obj_in: UserLoginSchema, session: Session = Depends(get_db)):
    return AuthService.login(session, obj_in)


@router.post("/auth/token")
def token(form_data: OAuth2PasswordRequestForm = Depends(), session: Session = Depends(get_db)):
    """Swagger OAuth2 表单提交"""
    login_data = UserLoginSchema(username=form_data.username, password=form_data.password)
    result = AuthService.login(session, login_data)
    return {"access_token": result["token"], "token_type": "bearer"}


@router.post("/auth/logout")
def logout():
    return {"message": "已登出"}
