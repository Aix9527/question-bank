from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


class LoginRequest(BaseModel):
    username: str = Field(min_length=1, max_length=64)
    # 密码允许为空（空密码账号直接留空登录），上限保持 256。
    password: str = Field(default='', max_length=256)


class UserRead(BaseModel):
    id: int
    username: str
    display_name: str | None
    role: str
    enabled: bool
    created_at: datetime


class LoginResponse(BaseModel):
    token: str
    expires_at: datetime
    user: UserRead


class AdminUserCreate(BaseModel):
    username: str = Field(min_length=1, max_length=64, pattern=r'^[A-Za-z0-9_.-]+$')
    # 密码允许为空（1 位或空均可），上限保持 256；管理员账号须在服务层校验非空。
    password: str = Field(default='', max_length=256)
    display_name: str | None = Field(default=None, max_length=128)
    role: str = Field(default='learner', pattern=r'^(learner|admin)$')


class AdminUserUpdate(BaseModel):
    display_name: str | None = Field(default=None, max_length=128)
    role: str | None = Field(default=None, pattern=r'^(learner|admin)$')
    enabled: bool | None = None
    # 密码允许为空（1 位或空均可），上限保持 256。
    password: str | None = Field(default=None, max_length=256)
