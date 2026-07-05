import re
import uuid
from datetime import datetime

from pydantic import BaseModel, EmailStr, field_validator

from app.models.user import UserRole


def _validate_password_strength(v: str) -> str:
    errors = []
    if len(v) < 12:
        errors.append("at least 12 characters")
    if not re.search(r"[A-Z]", v):
        errors.append("an uppercase letter")
    if not re.search(r"[a-z]", v):
        errors.append("a lowercase letter")
    if not re.search(r"\d", v):
        errors.append("a number")
    if not re.search(r"[!@#$%^&*()\-_=+\[\]{};:'\",.<>/?\\|`~]", v):
        errors.append("a special character")
    if errors:
        raise ValueError("Password must contain " + ", ".join(errors))
    return v


class UserCreate(BaseModel):
    email: EmailStr
    username: str
    password: str

    @field_validator("username")
    @classmethod
    def username_alphanumeric(cls, v: str) -> str:
        if not v.replace("_", "").replace("-", "").isalnum():
            raise ValueError("username may only contain letters, numbers, hyphens, and underscores")
        return v.lower()

    @field_validator("password")
    @classmethod
    def password_strong(cls, v: str) -> str:
        return _validate_password_strength(v)


class UserRead(BaseModel):
    model_config = {"from_attributes": True}

    id: uuid.UUID
    email: str
    username: str
    role: UserRole
    is_active: bool
    created_at: datetime


class UserUpdate(BaseModel):
    """Admin-only update — can change any field including role and active status."""
    email: EmailStr | None = None
    username: str | None = None
    role: UserRole | None = None
    is_active: bool | None = None


class UserSelfUpdate(BaseModel):
    """Self-service update — role and is_active are intentionally excluded."""
    email: EmailStr | None = None
    username: str | None = None
    password: str | None = None

    @field_validator("password")
    @classmethod
    def password_strong(cls, v: str | None) -> str | None:
        if v is not None:
            return _validate_password_strength(v)
        return v


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class Token(BaseModel):
    access_token: str
    token_type: str
