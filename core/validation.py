import re
from datetime import date, datetime

from pydantic import EmailStr, TypeAdapter, ValidationError


EMAIL_ADAPTER = TypeAdapter(EmailStr)
PHONE_ALLOWED_PATTERN = re.compile(r"^\+?[0-9 .()\-]{8,25}$")


def clean_text(value: str, label: str, max_length: int) -> str:
    cleaned = value.strip()
    if not cleaned:
        raise ValueError(f"{label} is required.")
    if len(cleaned) > max_length:
        raise ValueError(f"{label} must contain at most {max_length} characters.")
    return cleaned


def normalize_email(value: str) -> str:
    normalized = value.strip().lower()
    try:
        return str(EMAIL_ADAPTER.validate_python(normalized))
    except ValidationError as exc:
        raise ValueError("Please enter a valid email address.") from exc


def validate_password(value: str) -> str:
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
    raw_phone = value.strip()
    if not PHONE_ALLOWED_PATTERN.fullmatch(raw_phone):
        raise ValueError("Please enter a valid phone number.")

    has_international_prefix = raw_phone.startswith("+")
    digits = re.sub(r"\D", "", raw_phone)
    if not 8 <= len(digits) <= 15:
        raise ValueError("Phone number must contain between 8 and 15 digits.")
    return f"+{digits}" if has_international_prefix else digits


def parse_birth_date(value: str) -> date:
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
    try:
        start = datetime.strptime(date_start, "%Y-%m-%d")
        end = datetime.strptime(date_end, "%Y-%m-%d")
    except ValueError as exc:
        raise ValueError("Please enter valid start and end dates.") from exc

    if end < start:
        raise ValueError("End date must be after or equal to start date.")
    return start, end
