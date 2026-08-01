from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator

SPECIAL_CHARACTERS_SET = set("!@#$%^&*()_+-=[]{}|;:,.<>?")


def validate_password_complexity(password: str) -> str:
    if len(password) < 8:
        raise ValueError("Password must be at least 8 characters long")
    if not any(c.isupper() for c in password):
        raise ValueError("Password must contain at least 1 uppercase letter")
    if not any(c.islower() for c in password):
        raise ValueError("Password must contain at least 1 lowercase letter")
    if not any(c.isdigit() for c in password):
        raise ValueError("Password must contain at least 1 digit")
    if not any(c in SPECIAL_CHARACTERS_SET for c in password):
        raise ValueError(
            "Password must contain at least 1 special character (!@#$%^&*()_+-=[]{}|;:,.<>?)"
        )
    return password


class UserBase(BaseModel):
    email: str


class UserCreate(UserBase):
    password: str = Field(..., description="Password must meet complexity rules")
    full_name: str

    @field_validator("password")
    @classmethod
    def validate_password(cls, v: str) -> str:
        return validate_password_complexity(v)


class UserResponse(UserBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    full_name: str
    oauth_provider: Optional[str] = None
    is_active: bool
    created_at: datetime
    updated_at: datetime


class LoginRequest(BaseModel):
    email: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class PasswordResetRequest(BaseModel):
    email: str


class PasswordResetConfirm(BaseModel):
    token: str
    new_password: str = Field(..., description="Password must meet complexity rules")

    @field_validator("new_password")
    @classmethod
    def validate_new_password(cls, v: str) -> str:
        return validate_password_complexity(v)


class UserUpdate(BaseModel):
    full_name: Optional[str] = None
    password: Optional[str] = Field(
        None, description="Password must meet complexity rules"
    )

    @field_validator("password")
    @classmethod
    def validate_update_password(cls, v: Optional[str]) -> Optional[str]:
        if v is not None:
            return validate_password_complexity(v)
        return v

