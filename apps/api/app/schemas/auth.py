from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


class LoginRequest(BaseModel):
    username: str = Field(min_length=1, max_length=64)
    password: str = Field(min_length=1, max_length=256)


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
    password: str = Field(min_length=8, max_length=256)
    display_name: str | None = Field(default=None, max_length=128)
    role: str = Field(default='learner', pattern=r'^(learner|admin)$')


class AdminUserUpdate(BaseModel):
    display_name: str | None = Field(default=None, max_length=128)
    role: str | None = Field(default=None, pattern=r'^(learner|admin)$')
    enabled: bool | None = None
    password: str | None = Field(default=None, min_length=8, max_length=256)
