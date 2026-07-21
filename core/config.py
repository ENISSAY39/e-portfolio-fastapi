from functools import lru_cache
from typing import Literal

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables or ``.env``."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    app_env: Literal["development", "test", "production"] = "development"
    secret_key: str = Field(min_length=32)
    cookie_secure: bool | None = None
    seed_demo_data: bool | None = None
    access_token_expire_minutes: int = Field(default=60, ge=5, le=1440)

    @field_validator("secret_key")
    @classmethod
    def validate_secret_key(cls, value: str) -> str:
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
        return self.app_env == "production"

    @property
    def cookie_secure_enabled(self) -> bool:
        if self.cookie_secure is not None:
            return self.cookie_secure
        return self.is_production

    @property
    def seed_demo_data_enabled(self) -> bool:
        if self.seed_demo_data is not None:
            return self.seed_demo_data
        return not self.is_production


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
