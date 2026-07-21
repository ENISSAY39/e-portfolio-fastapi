"""Load and validate environment-dependent application configuration."""

from functools import lru_cache
from typing import Literal

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables or ``.env``.

    Environment variables take precedence over values in ``.env``. Unknown
    variables are ignored so this settings object can share a Compose env file
    with PostgreSQL without modelling every database-specific key.
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # The environment controls safe defaults, notably secure cookies and demo
    # data. Explicit values below may still override those defaults.
    app_env: Literal["development", "test", "production"] = "development"
    # JWT signatures are only as strong as this secret, hence the minimum size
    # and placeholder rejection performed below.
    secret_key: str = Field(min_length=32)
    # ``None`` delegates to an environment-sensitive default; an explicit value
    # remains useful for HTTPS test environments or local HTTP development.
    cookie_secure: bool | None = None
    # Seeding uses the same tri-state pattern and is safe-by-default in production.
    seed_demo_data: bool | None = None
    # Limit token lifetime to a practical range even when configured externally.
    access_token_expire_minutes: int = Field(default=60, ge=5, le=1440)

    @field_validator("secret_key")
    @classmethod
    def validate_secret_key(cls, value: str) -> str:
        """Reject blank padding and well-known placeholder signing secrets."""
        secret = value.strip()
        forbidden_values = {
            "replace-with-a-long-random-secret",
            "change-me",
            "secret",
        }
        if secret.lower() in forbidden_values:
            raise ValueError("SECRET_KEY still contains an insecure placeholder")
        return secret

    @property
    def is_production(self) -> bool:
        """Return whether production-safe defaults should be selected."""
        return self.app_env == "production"

    @property
    def cookie_secure_enabled(self) -> bool:
        """Resolve the cookie Secure flag from its override or environment."""
        if self.cookie_secure is not None:
            return self.cookie_secure
        # HTTPS-only cookies are mandatory by default in production, while local
        # HTTP development remains usable without a manual override.
        return self.is_production

    @property
    def seed_demo_data_enabled(self) -> bool:
        """Resolve demo-data seeding, defaulting to off in production."""
        if self.seed_demo_data is not None:
            return self.seed_demo_data
        return not self.is_production


@lru_cache
def get_settings() -> Settings:
    """Build settings once so every module observes one validated configuration."""
    return Settings()


# Importing ``settings`` fails fast when required configuration is unsafe or
# missing, before the application can start accepting requests.
settings = get_settings()
