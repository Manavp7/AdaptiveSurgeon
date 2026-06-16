"""Auth schemas."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"
    role: str
    username: str


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    username: str
    full_name: str
    role: str


class UserCreate(BaseModel):
    username: str
    password: str
    full_name: str = ""
    role: str = "viewer"
