"""PostgreSQL settings loaded from the backend environment file."""

from functools import lru_cache
from pathlib import Path

from pydantic import Field, SecretStr, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict
from sqlalchemy import URL

_BACKEND_DIRECTORY = Path(__file__).resolve().parents[2]


class DatabaseSettings(BaseSettings):
    """Validated PostgreSQL connection settings."""

    model_config = SettingsConfigDict(
        env_file=_BACKEND_DIRECTORY / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    host: str = Field(min_length=1, validation_alias="DATABASE_HOST")
    port: int = Field(ge=1, le=65535, validation_alias="DATABASE_PORT")
    name: str = Field(min_length=1, validation_alias="DATABASE_NAME")
    user: str = Field(min_length=1, validation_alias="DATABASE_USER")
    password: SecretStr = Field(validation_alias="DATABASE_PASSWORD")

    @field_validator("password")
    @classmethod
    def validate_password(cls, password: SecretStr) -> SecretStr:
        """Reject an empty database password without exposing its value."""
        if not password.get_secret_value():
            raise ValueError("DATABASE_PASSWORD must not be empty")
        return password

    @property
    def sqlalchemy_url(self) -> URL:
        """Build a psycopg SQLAlchemy URL without manual string escaping."""
        return URL.create(
            drivername="postgresql+psycopg",
            username=self.user,
            password=self.password.get_secret_value(),
            host=self.host,
            port=self.port,
            database=self.name,
        )


@lru_cache(maxsize=1)
def get_database_settings() -> DatabaseSettings:
    """Return the process-wide validated database settings."""
    return DatabaseSettings()
