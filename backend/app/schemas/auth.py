"""Authentication request and response schemas."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator


class AuthCredentials(BaseModel):
    """Credentials accepted during registration and login."""

    email: EmailStr
    password: str = Field(min_length=8, max_length=128)

    @field_validator("email", mode="before")
    @classmethod
    def normalize_email(cls, value: object) -> object:
        """Normalize email whitespace and casing before validation."""
        if isinstance(value, str):
            return value.strip().lower()
        return value


class UserResponse(BaseModel):
    """Public account information that never includes password data."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    email: EmailStr
    created_at: datetime
    updated_at: datetime
