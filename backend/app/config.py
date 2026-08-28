"""Application and authentication settings loaded from backend/.env."""

from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import Field, SecretStr, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

_BACKEND_DIRECTORY = Path(__file__).resolve().parents[1]


class EnvironmentSettings(BaseSettings):
    """Shared environment-file configuration."""

    model_config = SettingsConfigDict(
        env_file=_BACKEND_DIRECTORY / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


class ApplicationSettings(EnvironmentSettings):
    """Non-secret web application settings."""

    frontend_origin: str = Field(
        default="http://localhost:3000",
        min_length=1,
        validation_alias="FRONTEND_ORIGIN",
    )

    @field_validator("frontend_origin", mode="before")
    @classmethod
    def normalize_frontend_origin(cls, value: object) -> object:
        """Remove whitespace and a trailing slash for exact CORS matching."""
        if isinstance(value, str):
            return value.strip().rstrip("/")
        return value


class AuthSettings(EnvironmentSettings):
    """Validated settings used to sign and transport authentication tokens."""

    secret_key: SecretStr = Field(
        min_length=32,
        validation_alias="AUTH_SECRET_KEY",
    )
    token_expire_minutes: int = Field(
        default=480,
        ge=5,
        le=10080,
        validation_alias="AUTH_TOKEN_EXPIRE_MINUTES",
    )
    cookie_name: str = Field(
        default="parcelpulse_session",
        min_length=1,
        max_length=100,
        pattern=r"^[A-Za-z0-9_-]+$",
        validation_alias="AUTH_COOKIE_NAME",
    )
    cookie_secure: bool = Field(
        default=False,
        validation_alias="AUTH_COOKIE_SECURE",
    )
    cookie_samesite: Literal["lax", "strict", "none"] = Field(
        default="lax",
        validation_alias="AUTH_COOKIE_SAMESITE",
    )

    @field_validator("secret_key")
    @classmethod
    def reject_placeholder_secret(cls, value: SecretStr) -> SecretStr:
        """Prevent documented placeholder values from signing sessions."""
        normalized = value.get_secret_value().lower()
        if normalized.startswith(
            ("replace_", "change_", "generate_", "paste_")
        ):
            raise ValueError("AUTH_SECRET_KEY must be a generated random value")
        return value

    @model_validator(mode="after")
    def validate_cookie_security(self) -> "AuthSettings":
        """SameSite=None cookies must also use the Secure attribute."""
        if self.cookie_samesite == "none" and not self.cookie_secure:
            raise ValueError(
                "AUTH_COOKIE_SECURE must be true when AUTH_COOKIE_SAMESITE=none"
            )
        return self

    @property
    def token_expire_seconds(self) -> int:
        """Return the configured token lifetime in seconds."""
        return self.token_expire_minutes * 60


@lru_cache(maxsize=1)
def get_application_settings() -> ApplicationSettings:
    """Return cached non-secret application settings."""
    return ApplicationSettings()


@lru_cache(maxsize=1)
def get_auth_settings() -> AuthSettings:
    """Return cached authentication settings."""
    return AuthSettings()
