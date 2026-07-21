"""Normalize and validate untrusted values submitted through HTML forms."""

import re
from datetime import date, datetime
from urllib.parse import urlsplit

from pydantic import EmailStr, TypeAdapter, ValidationError


# Reuse Pydantic's well-tested email parser instead of maintaining an incomplete
# email regular expression locally.
EMAIL_ADAPTER = TypeAdapter(EmailStr)
# The first pass accepts common human formatting; a second pass below enforces
# the number of digits after punctuation and spaces are removed.
PHONE_ALLOWED_PATTERN = re.compile(r"^\+?[0-9 .()\-]{8,25}$")


def clean_text(value: str, label: str, max_length: int) -> str:
    """Trim required text and enforce the field-specific storage limit."""
    cleaned = value.strip()
    if not cleaned:
        raise ValueError(f"{label} is required.")
    if len(cleaned) > max_length:
        raise ValueError(f"{label} must contain at most {max_length} characters.")
    return cleaned


def clean_optional_text(
    value: str,
    label: str,
    max_length: int,
) -> str | None:
    """Trim optional text and return ``None`` when the field is blank."""
    cleaned = value.strip()
    if not cleaned:
        return None
    if len(cleaned) > max_length:
        raise ValueError(f"{label} must contain at most {max_length} characters.")
    return cleaned


def parse_skill_level(value: str) -> int:
    """Parse the five-point proficiency selected by a skill form."""
    try:
        level = int(value)
    except ValueError as exc:
        raise ValueError("Skill level must be a whole number from 1 to 5.") from exc

    if not 1 <= level <= 5:
        raise ValueError("Skill level must be between 1 and 5.")
    return level


def validate_http_url(
    value: str,
    label: str,
    *,
    required: bool = False,
) -> str | None:
    """Validate an optional absolute HTTP(S) destination from a form."""
    cleaned = value.strip()
    if not cleaned:
        if required:
            raise ValueError(f"{label} is required.")
        return None
    if len(cleaned) > 2048:
        raise ValueError(f"{label} must contain at most 2048 characters.")
    if any(character.isspace() for character in cleaned):
        raise ValueError(f"{label} must be a valid HTTP or HTTPS URL.")

    try:
        parsed = urlsplit(cleaned)
        # Accessing ``hostname`` and ``port`` also rejects malformed bracketed
        # hosts and non-numeric or out-of-range ports.
        hostname = parsed.hostname
        parsed.port
    except ValueError as exc:
        raise ValueError(f"{label} must be a valid HTTP or HTTPS URL.") from exc

    if parsed.scheme.lower() not in {"http", "https"} or not hostname:
        raise ValueError(f"{label} must be a valid HTTP or HTTPS URL.")
    return cleaned


def normalize_email(value: str) -> str:
    """Return a validated lowercase email for consistent unique lookups."""
    normalized = value.strip().lower()
    try:
        return str(EMAIL_ADAPTER.validate_python(normalized))
    except ValidationError as exc:
        raise ValueError("Please enter a valid email address.") from exc


def validate_password(value: str) -> str:
    """Enforce the application's length and character-class password policy."""
    # Validate the original value: silently trimming a password would change the
    # credential the user intentionally entered.
    if len(value) < 10:
        raise ValueError("Password must contain at least 10 characters.")
    if len(value) > 128:
        raise ValueError("Password must contain at most 128 characters.")
    if not re.search(r"[a-z]", value):
        raise ValueError("Password must contain a lowercase letter.")
    if not re.search(r"[A-Z]", value):
        raise ValueError("Password must contain an uppercase letter.")
    if not re.search(r"\d", value):
        raise ValueError("Password must contain a number.")
    return value


def normalize_phone(value: str) -> str:
    """Validate a phone number and store a punctuation-free representation."""
    raw_phone = value.strip()
    if not PHONE_ALLOWED_PATTERN.fullmatch(raw_phone):
        raise ValueError("Please enter a valid phone number.")

    # Preserve only whether the user supplied an international prefix; all
    # display punctuation is removed to keep storage and comparisons consistent.
    has_international_prefix = raw_phone.startswith("+")
    digits = re.sub(r"\D", "", raw_phone)
    if not 8 <= len(digits) <= 15:
        raise ValueError("Phone number must contain between 8 and 15 digits.")
    return f"+{digits}" if has_international_prefix else digits


def parse_birth_date(value: str) -> date:
    """Parse an ISO birth date and reject future or implausibly old values."""
    try:
        birth_date = date.fromisoformat(value)
    except ValueError as exc:
        raise ValueError("Please enter a valid birth date.") from exc

    today = date.today()
    if birth_date >= today:
        raise ValueError("Birth date must be in the past.")
    if birth_date.year < today.year - 120:
        raise ValueError("Please enter a realistic birth date.")
    return birth_date


def parse_date_range(date_start: str, date_end: str) -> tuple[datetime, datetime]:
    """Parse an HTML date pair and enforce chronological ordering."""
    try:
        start = datetime.strptime(date_start, "%Y-%m-%d")
        end = datetime.strptime(date_end, "%Y-%m-%d")
    except ValueError as exc:
        raise ValueError("Please enter valid start and end dates.") from exc

    if end < start:
        raise ValueError("End date must be after or equal to start date.")
    return start, end
