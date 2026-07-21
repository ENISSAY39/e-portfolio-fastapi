"""Tests for validated and environment-sensitive application settings."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from core.config import Settings, get_settings


VALID_SECRET = "a-valid-test-secret-with-at-least-32-characters"


def build_settings(**overrides: object) -> Settings:
    """Build settings independently from the test runner's environment."""
    values: dict[str, object] = {
        "_env_file": None,
        "app_env": "development",
        "secret_key": VALID_SECRET,
        "cookie_secure": None,
        "seed_demo_data": None,
    }
    values.update(overrides)
    return Settings(**values)


def test_development_uses_local_safe_defaults() -> None:
    settings = build_settings(app_env="development")

    assert settings.is_production is False
    assert settings.cookie_secure_enabled is False
    assert settings.seed_demo_data_enabled is True
    assert settings.access_token_expire_minutes == 60


def test_production_uses_production_safe_defaults() -> None:
    settings = build_settings(app_env="production")

    assert settings.is_production is True
    assert settings.cookie_secure_enabled is True
    assert settings.seed_demo_data_enabled is False


@pytest.mark.parametrize(
    ("app_env", "cookie_secure", "seed_demo_data"),
    [
        ("development", True, False),
        ("production", False, True),
    ],
)
def test_explicit_cookie_and_seed_overrides_take_priority(
    app_env: str,
    cookie_secure: bool,
    seed_demo_data: bool,
) -> None:
    settings = build_settings(
        app_env=app_env,
        cookie_secure=cookie_secure,
        seed_demo_data=seed_demo_data,
    )

    assert settings.cookie_secure_enabled is cookie_secure
    assert settings.seed_demo_data_enabled is seed_demo_data


def test_secret_key_is_trimmed() -> None:
    settings = build_settings(secret_key=f"  {VALID_SECRET}  ")

    assert settings.secret_key == VALID_SECRET


def test_insecure_secret_placeholder_is_rejected() -> None:
    with pytest.raises(ValidationError, match="insecure placeholder"):
        build_settings(secret_key="replace-with-a-long-random-secret")


@pytest.mark.parametrize(
    "overrides",
    [
        {"secret_key": "too-short"},
        {"app_env": "staging"},
        {"access_token_expire_minutes": 4},
        {"access_token_expire_minutes": 1441},
    ],
)
def test_invalid_settings_are_rejected(overrides: dict[str, object]) -> None:
    with pytest.raises(ValidationError):
        build_settings(**overrides)


def test_get_settings_reads_environment_once(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    get_settings.cache_clear()
    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.setenv("SECRET_KEY", VALID_SECRET)
    monkeypatch.delenv("COOKIE_SECURE", raising=False)
    monkeypatch.delenv("SEED_DEMO_DATA", raising=False)

    try:
        first_settings = get_settings()
        monkeypatch.setenv("APP_ENV", "development")
        second_settings = get_settings()

        assert first_settings is second_settings
        assert first_settings.is_production is True
    finally:
        get_settings.cache_clear()
