from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class UserRegister(BaseModel):
    email: str
    password: str = Field(min_length=8)
    role: str = "patient"
    preferred_language: str | None = None
    timezone: str | None = None
    prefers_de_identified: bool = False
    data_residency_region: str = "in"


class UserPublic(BaseModel):
    user_id: str
    email: str | None = None
    role: str
    is_active: bool
    prefers_de_identified: bool
    data_residency_region: str
    anonymized: bool
    created_at: datetime | None = None


class TokenPair(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class LoginRequest(BaseModel):
    email: str
    password: str


class RoleChangeRequest(BaseModel):
    new_role: str
