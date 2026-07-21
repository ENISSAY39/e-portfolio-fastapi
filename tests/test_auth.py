"""Integration tests for registration and cookie-based authentication routes."""

from __future__ import annotations

from collections.abc import Callable
from datetime import datetime, timedelta, timezone

import jwt
import pytest
from fastapi.testclient import TestClient
from httpx import Response
from sqlmodel import Session, select

from core.config import settings
from core.security import ALGORITHM, verify_password
from schemas.User import User


VALID_PASSWORD = "ValidPass123"
REGISTRATION_DATA = {
    "name": "  Lovelace  ",
    "first_name": "  Ada  ",
    "birth_date": "1990-01-01",
    "mail": "  Ada.Lovelace@Example.COM  ",
    "phone": "+33 (0)6 12 34 56 78",
    "password": VALID_PASSWORD,
}


def test_registration_normalizes_and_hashes_account_data(
    client: TestClient,
    session: Session,
    csrf_token: Callable[[str], str],
) -> None:
    form_data = {**REGISTRATION_DATA, "csrf_token": csrf_token("/create_user")}

    response = client.post(
        "/create_user",
        data=form_data,
        follow_redirects=False,
    )

    assert response.status_code == 303
    assert response.headers["location"] == "/login"

    user = session.exec(
        select(User).where(User.mail == "ada.lovelace@example.com")
    ).one()
    assert user.name == "Lovelace"
    assert user.first_name == "Ada"
    assert user.phone == "+330612345678"
    assert user.hashed_password != VALID_PASSWORD
    assert verify_password(VALID_PASSWORD, user.hashed_password) is True


def test_registration_rejects_a_duplicate_normalized_email(
    client: TestClient,
    session: Session,
    user_factory: Callable[..., User],
    csrf_token: Callable[[str], str],
) -> None:
    user_factory(mail="ada@example.com")
    form_data = {
        **REGISTRATION_DATA,
        "mail": "  ADA@EXAMPLE.COM ",
        "csrf_token": csrf_token("/create_user"),
    }

    response = client.post("/create_user", data=form_data)

    assert response.status_code == 409
    assert "An account already exists with this email address." in response.text
    session.expire_all()
    assert len(session.exec(select(User)).all()) == 1


def test_registration_returns_validation_errors_without_creating_an_account(
    client: TestClient,
    session: Session,
    csrf_token: Callable[[str], str],
) -> None:
    form_data = {
        **REGISTRATION_DATA,
        "password": "too-short",
        "csrf_token": csrf_token("/create_user"),
    }

    response = client.post("/create_user", data=form_data)

    assert response.status_code == 400
    assert "Password must contain at least 10 characters." in response.text
    assert session.exec(select(User)).all() == []
    assert "too-short" not in response.text


@pytest.mark.parametrize(
    ("path", "form_data"),
    [
        pytest.param("/create_user", REGISTRATION_DATA, id="registration"),
        pytest.param(
            "/login",
            {"mail": "ada@example.com", "password": VALID_PASSWORD},
            id="login",
        ),
        pytest.param("/logout", {}, id="logout"),
    ],
)
def test_authentication_mutations_reject_a_missing_csrf_token(
    client: TestClient,
    path: str,
    form_data: dict[str, str],
) -> None:
    response = client.post(path, data=form_data, follow_redirects=False)

    assert response.status_code == 403
    assert response.json() == {"detail": "Invalid or expired CSRF token"}


def test_login_rejects_a_mismatched_csrf_token(
    client: TestClient,
    csrf_token: Callable[[str], str],
) -> None:
    csrf_token("/login")

    response = client.post(
        "/login",
        data={
            "mail": "ada@example.com",
            "password": VALID_PASSWORD,
            "csrf_token": "different-token",
        },
    )

    assert response.status_code == 403
    assert response.json() == {"detail": "Invalid or expired CSRF token"}


def test_login_normalizes_email_and_sets_a_protected_access_cookie(
    client: TestClient,
    user_factory: Callable[..., User],
    login_user: Callable[..., Response],
) -> None:
    user_factory(mail="ada@example.com")

    response = login_user("  ADA@EXAMPLE.COM  ", VALID_PASSWORD)

    assert response.status_code == 303
    assert response.headers["location"] == "/profil"
    cookie_header = response.headers["set-cookie"]
    assert "access_token=" in cookie_header
    assert "HttpOnly" in cookie_header
    assert "SameSite=lax" in cookie_header
    assert client.cookies.get("access_token") is not None

    profile_response = client.get("/profil")
    assert profile_response.status_code == 200
    assert "ada@example.com" in profile_response.text
    assert profile_response.headers["cache-control"] == "no-cache, no-store, must-revalidate"


@pytest.mark.parametrize(
    ("mail", "password"),
    [
        pytest.param("unknown@example.com", VALID_PASSWORD, id="unknown-email"),
        pytest.param("ada@example.com", "WrongPassword9", id="wrong-password"),
        pytest.param("not-an-email", VALID_PASSWORD, id="malformed-email"),
    ],
)
def test_login_returns_one_generic_error_for_invalid_credentials(
    client: TestClient,
    user_factory: Callable[..., User],
    login_user: Callable[..., Response],
    mail: str,
    password: str,
) -> None:
    user_factory(mail="ada@example.com")

    response = login_user(mail, password)

    assert response.status_code == 401
    assert "Invalid email or password." in response.text
    assert client.cookies.get("access_token") is None


def test_logout_deletes_authentication_and_csrf_cookies(
    authenticated_client: TestClient,
    csrf_token: Callable[[str], str],
) -> None:
    token = csrf_token("/profil")

    response = authenticated_client.post(
        "/logout",
        data={"csrf_token": token},
        follow_redirects=False,
    )

    assert response.status_code == 303
    assert response.headers["location"] == "/"
    assert authenticated_client.cookies.get("access_token") is None
    assert authenticated_client.cookies.get("csrf_token") is None

    private_response = authenticated_client.get("/profil", follow_redirects=False)
    assert private_response.status_code == 303
    assert private_response.headers["location"] == "/login"


@pytest.mark.parametrize(
    "access_token",
    [None, "not-a-jwt"],
    ids=["missing", "malformed"],
)
def test_profile_redirects_for_missing_or_malformed_authentication(
    client: TestClient,
    access_token: str | None,
) -> None:
    if access_token is not None:
        client.cookies.set("access_token", access_token)

    response = client.get("/profil", follow_redirects=False)

    assert response.status_code == 303
    assert response.headers["location"] == "/login"


def test_profile_redirects_for_an_expired_access_token(client: TestClient) -> None:
    expired_token = jwt.encode(
        {
            "sub": "ada@example.com",
            "exp": datetime.now(timezone.utc) - timedelta(seconds=1),
        },
        settings.secret_key,
        algorithm=ALGORITHM,
    )
    client.cookies.set("access_token", expired_token)

    response = client.get("/profil", follow_redirects=False)

    assert response.status_code == 303
    assert response.headers["location"] == "/login"


def test_profile_redirects_when_a_valid_token_references_no_user(
    client: TestClient,
) -> None:
    token = jwt.encode(
        {
            "sub": "deleted@example.com",
            "exp": datetime.now(timezone.utc) + timedelta(minutes=5),
        },
        settings.secret_key,
        algorithm=ALGORITHM,
    )
    client.cookies.set("access_token", token)

    response = client.get("/profil", follow_redirects=False)

    assert response.status_code == 303
    assert response.headers["location"] == "/login"
