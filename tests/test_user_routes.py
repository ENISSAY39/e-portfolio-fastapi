"""Regression tests for public profiles and defensive user-route branches."""

from __future__ import annotations

from collections.abc import Callable
from datetime import date, datetime

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.exc import IntegrityError
from sqlmodel import Session, select

import core.authentication as authentication_module
import routers.user as user_routes
from schemas.Education import Education
from schemas.Experiences import Experience
from schemas.User import User


REGISTRATION_DATA = {
    "name": "Lovelace",
    "first_name": "Ada",
    "birth_date": "1990-01-01",
    "mail": "ada@example.com",
    "phone": "+33 6 12 34 56 78",
    "password": "ValidPass123",
}


def test_public_portfolio_renders_only_the_requested_users_records(
    client: TestClient,
    session: Session,
    user_factory: Callable[..., User],
) -> None:
    owner = user_factory(mail="owner@example.com", first_name="PortfolioOwner")
    other_user = user_factory(mail="other@example.com", first_name="OtherUser")
    assert owner.id is not None
    assert other_user.id is not None

    session.add_all(
        [
            Experience(
                title="Owner role",
                date_start=datetime(2020, 1, 1),
                date_end=datetime(2021, 1, 1),
                description="Owner experience description",
                company="Owner Company",
                user_id=owner.id,
            ),
            Experience(
                title="Hidden role",
                date_start=datetime(2020, 1, 1),
                date_end=datetime(2021, 1, 1),
                description="Other experience description",
                company="Other Company",
                user_id=other_user.id,
            ),
            Education(
                school_name="Owner University",
                date_start=datetime(2015, 9, 1),
                date_end=datetime(2019, 6, 1),
                description="Owner education description",
                major="Computer Science",
                user_id=owner.id,
            ),
            Education(
                school_name="Hidden University",
                date_start=datetime(2015, 9, 1),
                date_end=datetime(2019, 6, 1),
                description="Other education description",
                major="Physics",
                user_id=other_user.id,
            ),
        ]
    )
    session.commit()

    response = client.get(f"/portfolio/{owner.id}")

    assert response.status_code == 200
    assert "PortfolioOwner Lovelace" in response.text
    assert "Owner role" in response.text
    assert "Owner Company" in response.text
    assert "Owner University" in response.text
    assert "Computer Science" in response.text
    assert "Hidden role" not in response.text
    assert "Hidden University" not in response.text
    assert response.context["user"].id == owner.id
    assert {item.user_id for item in response.context["experiences"]} == {owner.id}
    assert {item.user_id for item in response.context["educations"]} == {owner.id}


def test_public_portfolio_redirects_for_an_unknown_user(
    client: TestClient,
) -> None:
    response = client.get("/portfolio/999999", follow_redirects=False)

    assert response.status_code == 303
    assert response.headers["location"] == "/login"


def test_calculate_age_subtracts_one_before_the_birthday(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class FixedDate(date):
        @classmethod
        def today(cls) -> FixedDate:
            return cls(2026, 7, 21)

    monkeypatch.setattr(user_routes, "date", FixedDate)

    assert user_routes.calculate_age(date(2000, 7, 22)) == 25


def test_registration_rolls_back_a_concurrent_email_conflict(
    client: TestClient,
    session: Session,
    csrf_token: Callable[[str], str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    form_data = {
        **REGISTRATION_DATA,
        "csrf_token": csrf_token("/create_user"),
    }
    rollback_calls = 0
    original_rollback = Session.rollback

    def raise_unique_conflict(database_session: Session) -> None:
        raise IntegrityError(
            "INSERT INTO user (...) VALUES (...)",
            {},
            RuntimeError("simulated concurrent unique constraint violation"),
        )

    def record_rollback(database_session: Session) -> None:
        nonlocal rollback_calls
        rollback_calls += 1
        original_rollback(database_session)

    monkeypatch.setattr(Session, "commit", raise_unique_conflict)
    monkeypatch.setattr(Session, "rollback", record_rollback)

    response = client.post("/create_user", data=form_data)

    assert response.status_code == 409
    assert "An account already exists with this email address." in response.text
    assert rollback_calls == 1
    assert session.exec(select(User)).all() == []


def test_profile_rejects_a_decoded_token_with_a_non_string_subject(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        authentication_module,
        "decode_access_token",
        lambda token: {"sub": 123},
    )
    client.cookies.set("access_token", "syntactically-irrelevant-test-token")

    response = client.get("/profil", follow_redirects=False)

    assert response.status_code == 303
    assert response.headers["location"] == "/login"
