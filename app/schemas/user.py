"""用户 Schema"""
from datetime import datetime
from typing import Optional, List

from pydantic import BaseModel, Field, EmailStr


class UserCreateSchema(BaseModel):
    username: str = Field(..., description="用户名")
    password: str = Field(..., min_length=8, description="密码")
    phone: Optional[str] = Field(None, description="手机号")
    email: Optional[EmailStr] = Field(None, description="邮箱")
    real_name: Optional[str] = Field(None, description="真实姓名")
    passenger_id: Optional[str] = Field(None, description="关联旅客ID")


class UserUpdateSchema(BaseModel):
    username: Optional[str] = Field(None, description="用户名")
    password: Optional[str] = Field(None, min_length=8, description="密码")
    phone: Optional[str] = Field(None, description="手机号")
    email: Optional[EmailStr] = Field(None, description="邮箱")
    real_name: Optional[str] = Field(None, description="真实姓名")
    passenger_id: Optional[str] = Field(None, description="关联旅客ID")


class UserLoginSchema(BaseModel):
    username: str = Field(..., description="用户名")
    password: str = Field(..., description="密码")


class UserResponseSchema(BaseModel):
    id: int
    username: str
    phone: Optional[str] = None
    email: Optional[str] = None
    real_name: Optional[str] = None
    passenger_id: Optional[str] = None
    create_time: Optional[datetime] = None
    update_time: Optional[datetime] = None

    class Config:
        from_attributes = True


class UserLoginResponseSchema(BaseModel):
    id: int
    username: str
    token: str
    phone: Optional[str] = None
    real_name: Optional[str] = None
