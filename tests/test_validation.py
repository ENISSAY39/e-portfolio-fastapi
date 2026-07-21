"""Unit tests for normalization and form-validation helpers."""

from datetime import date, datetime, timedelta

import pytest

from core.validation import (
    clean_optional_text,
    clean_text,
    normalize_email,
    normalize_phone,
    parse_birth_date,
    parse_date_range,
    parse_skill_level,
    validate_http_url,
    validate_password,
)


def test_clean_text_trims_surrounding_whitespace() -> None:
    assert clean_text("  FastAPI developer  ", "Title", 30) == "FastAPI developer"


@pytest.mark.parametrize(
    ("value", "max_length", "expected_message"),
    [
        ("   ", 20, "Name is required."),
        ("portfolio", 8, "Name must contain at most 8 characters."),
    ],
)
def test_clean_text_rejects_invalid_values(
    value: str,
    max_length: int,
    expected_message: str,
) -> None:
    with pytest.raises(ValueError) as exc_info:
        clean_text(value, "Name", max_length)

    assert str(exc_info.value) == expected_message


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        ("   ", None),
        ("  Open-source contributor  ", "Open-source contributor"),
    ],
)
def test_clean_optional_text_normalizes_blank_and_present_values(
    value: str,
    expected: str | None,
) -> None:
    assert clean_optional_text(value, "Biography", 100) == expected


def test_clean_optional_text_rejects_an_overlong_value() -> None:
    with pytest.raises(
        ValueError,
        match="^Biography must contain at most 10 characters\\.$",
    ):
        clean_optional_text("x" * 11, "Biography", 10)


@pytest.mark.parametrize("value", ["1", "3", "5"])
def test_parse_skill_level_accepts_the_five_point_range(value: str) -> None:
    assert parse_skill_level(value) == int(value)


@pytest.mark.parametrize(
    ("value", "expected_message"),
    [
        ("advanced", "Skill level must be a whole number from 1 to 5."),
        ("0", "Skill level must be between 1 and 5."),
        ("6", "Skill level must be between 1 and 5."),
    ],
)
def test_parse_skill_level_rejects_invalid_values(
    value: str,
    expected_message: str,
) -> None:
    with pytest.raises(ValueError) as exc_info:
        parse_skill_level(value)

    assert str(exc_info.value) == expected_message


@pytest.mark.parametrize(
    "value",
    [
        "https://portfolio.example/projects/1?source=test#demo",
        "http://localhost:8000/demo",
    ],
)
def test_validate_http_url_accepts_absolute_http_destinations(value: str) -> None:
    assert validate_http_url(f"  {value}  ", "Project URL") == value


def test_validate_http_url_normalizes_an_optional_blank_value() -> None:
    assert validate_http_url("   ", "Project URL") is None


@pytest.mark.parametrize(
    ("value", "expected_message"),
    [
        ("", "URL is required."),
        ("javascript:alert(1)", "URL must be a valid HTTP or HTTPS URL."),
        ("https://", "URL must be a valid HTTP or HTTPS URL."),
        ("https://example.com/a path", "URL must be a valid HTTP or HTTPS URL."),
        ("https://example.com:invalid", "URL must be a valid HTTP or HTTPS URL."),
        ("https://[invalid", "URL must be a valid HTTP or HTTPS URL."),
        ("https://example.com/" + "x" * 2030, "URL must contain at most 2048 characters."),
    ],
)
def test_validate_http_url_rejects_missing_or_unsafe_destinations(
    value: str,
    expected_message: str,
) -> None:
    with pytest.raises(ValueError) as exc_info:
        validate_http_url(value, "URL", required=True)

    assert str(exc_info.value) == expected_message


def test_normalize_email_trims_and_lowercases_a_valid_address() -> None:
    assert normalize_email("  Ada.Lovelace@Example.COM  ") == "ada.lovelace@example.com"


@pytest.mark.parametrize("value", ["not-an-email", "missing-domain@", "@example.com"])
def test_normalize_email_rejects_invalid_addresses(value: str) -> None:
    with pytest.raises(ValueError, match="^Please enter a valid email address\\.$"):
        normalize_email(value)


def test_validate_password_accepts_a_strong_password_without_modifying_it() -> None:
    password = "  StrongPassword1  "

    assert validate_password(password) == password


@pytest.mark.parametrize(
    ("password", "expected_message"),
    [
        ("Short1A", "Password must contain at least 10 characters."),
        ("Aa1" + "x" * 126, "Password must contain at most 128 characters."),
        ("UPPERCASE123", "Password must contain a lowercase letter."),
        ("lowercase123", "Password must contain an uppercase letter."),
        ("NoNumberHere", "Password must contain a number."),
    ],
)
def test_validate_password_rejects_passwords_outside_policy(
    password: str,
    expected_message: str,
) -> None:
    with pytest.raises(ValueError) as exc_info:
        validate_password(password)

    assert str(exc_info.value) == expected_message


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        ("+33 (0)6 12 34 56 78", "+330612345678"),
        ("06.12.34.56.78", "0612345678"),
    ],
)
def test_normalize_phone_removes_display_punctuation(value: str, expected: str) -> None:
    assert normalize_phone(value) == expected


@pytest.mark.parametrize(
    ("value", "expected_message"),
    [
        ("06 12 CALL ME", "Please enter a valid phone number."),
        ("12 34567", "Phone number must contain between 8 and 15 digits."),
        ("1234567890123456", "Phone number must contain between 8 and 15 digits."),
    ],
)
def test_normalize_phone_rejects_invalid_numbers(
    value: str,
    expected_message: str,
) -> None:
    with pytest.raises(ValueError) as exc_info:
        normalize_phone(value)

    assert str(exc_info.value) == expected_message


def test_parse_birth_date_returns_a_date_for_valid_iso_input() -> None:
    assert parse_birth_date("2000-02-29") == date(2000, 2, 29)


def test_parse_birth_date_rejects_an_invalid_calendar_date() -> None:
    with pytest.raises(ValueError, match="^Please enter a valid birth date\\.$"):
        parse_birth_date("2000-02-30")


def test_parse_birth_date_rejects_today() -> None:
    with pytest.raises(ValueError, match="^Birth date must be in the past\\.$"):
        parse_birth_date(date.today().isoformat())


def test_parse_birth_date_rejects_an_implausibly_old_date() -> None:
    implausible_year = date.today().year - 121

    with pytest.raises(ValueError, match="^Please enter a realistic birth date\\.$"):
        parse_birth_date(f"{implausible_year}-01-01")


def test_parse_date_range_accepts_equal_dates() -> None:
    expected = datetime(2026, 7, 21)

    assert parse_date_range("2026-07-21", "2026-07-21") == (expected, expected)


def test_parse_date_range_accepts_chronological_dates() -> None:
    start = datetime(2024, 1, 1)
    end = start + timedelta(days=31)

    assert parse_date_range("2024-01-01", "2024-02-01") == (start, end)


def test_parse_date_range_rejects_invalid_date_input() -> None:
    with pytest.raises(
        ValueError,
        match="^Please enter valid start and end dates\\.$",
    ):
        parse_date_range("2024-02-30", "2024-03-01")


def test_parse_date_range_rejects_an_end_before_the_start() -> None:
    with pytest.raises(
        ValueError,
        match="^End date must be after or equal to start date\\.$",
    ):
        parse_date_range("2024-02-01", "2024-01-31")
