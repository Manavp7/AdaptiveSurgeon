"""Minimal RBAC user model.

Roles: admin | surgeon | viewer. Passwords are stored as salted PBKDF2 hashes
using the stdlib only (no external auth dependency).
"""

from __future__ import annotations

from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column

from ..db import Base
from .base import IdMixin, TimestampMixin


class User(IdMixin, TimestampMixin, Base):
    __tablename__ = "users"

    username: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    full_name: Mapped[str] = mapped_column(String(120), default="")
    role: Mapped[str] = mapped_column(String(16), default="viewer")  # admin|surgeon|viewer
    password_hash: Mapped[str] = mapped_column(String(255))
