"""用户 ORM 模型"""
from datetime import datetime
from typing import Optional

from sqlalchemy import String, DateTime, func
from sqlalchemy.orm import Mapped, mapped_column

from db import DBModelBase


class UserModel(DBModelBase):
    username: Mapped[str] = mapped_column(String(20), unique=True, nullable=False)
    password: Mapped[str] = mapped_column(String(200), nullable=False)
    phone: Mapped[Optional[str]] = mapped_column(String(20), nullable=True, comment="手机号码")
    email: Mapped[Optional[str]] = mapped_column(String(50), nullable=True, comment="邮箱地址")
    real_name: Mapped[Optional[str]] = mapped_column(String(50), nullable=True, comment="真实姓名")
    passenger_id: Mapped[Optional[str]] = mapped_column(String(50), nullable=True, comment="关联旅客ID")
