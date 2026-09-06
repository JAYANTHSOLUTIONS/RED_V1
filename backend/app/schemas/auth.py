"""Authentication and Authorization Pydantic schemas.

Strictly validates input payloads and filters output representations so that
passwords, password hashes, and internal tokens are never serialized or leaked.
"""
from datetime import datetime
from typing import Optional
import uuid

from pydantic import BaseModel, ConfigDict, Field


class LoginRequest(BaseModel):
    email: str = Field(
        ...,
        max_length=255,
        pattern=r"^[^\s@]+@[^\s@]+\.[^\s@]+$",
        description="Consultant login email address",
    )
    password: str = Field(..., min_length=1, description="Account password")


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int = Field(..., description="Access token lifetime in seconds")
    user: Optional["UserResponse"] = None


class RefreshTokenRequest(BaseModel):
    refresh_token: str = Field(..., min_length=1, description="Opaque refresh token")


class UserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    email: str
    full_name: str
    phone: Optional[str] = None
    role: str
    is_active: bool
    created_at: datetime
