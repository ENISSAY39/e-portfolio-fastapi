"""Integration coverage for editable Sprint 2 portfolio content."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import date
from typing import Any

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.exc import IntegrityError
from sqlmodel import Session, SQLModel, select

from core.security import create_access_token, decode_access_token
from schemas.Links import ExternalLink
from schemas.Projects import Project
from schemas.Skills import Skill
from schemas.User import User


PROFILE_DATA = {
    "name": "Lovelace",
    "first_name": "Ada",
    "birth_date": "1990-01-01",
    "mail": "ada@example.com",
    "phone": "0612345678",
    "bio": "Mathematician and software pioneer.",
}


@dataclass(frozen=True)
class ResourceCase:
    """Describe one owned content resource for parametrized route tests."""

    model: type[SQLModel]
    resource: str
    context_name: str
    initial_fields: dict[str, Any]
    create_data: dict[str, str]
    created_fields: dict[str, Any]
    update_data: dict[str, str]
    updated_fields: dict[str, Any]
    invalid_data: dict[str, str]


RESOURCE_CASES = (
    ResourceCase(
        model=Skill,
        resource="skill",
        context_name="skill",
        initial_fields={"name": "Original skill", "level": 2},
        create_data={"name": "  Python  ", "level": "4"},
        created_fields={"name": "Python", "level": 4},
        update_data={"name": "  FastAPI  ", "level": "5"},
        updated_fields={"name": "FastAPI", "level": 5},
        invalid_data={"name": "   ", "level": "3"},
    ),
    ResourceCase(
        model=Project,
        resource="project",
        context_name="project",
        initial_fields={
            "title": "Original project",
            "description": "Original description",
            "technologies": "Python",
            "project_url": "https://original.example",
            "repository_url": "https://github.com/example/original",
        },
        create_data={
            "title": "  Portfolio platform  ",
            "description": "  A server-rendered portfolio.  ",
            "technologies": "  FastAPI, SQLModel  ",
            "project_url": "  https://portfolio.example/demo  ",
            "repository_url": "   ",
        },
        created_fields={
            "title": "Portfolio platform",
            "description": "A server-rendered portfolio.",
            "technologies": "FastAPI, SQLModel",
            "project_url": "https://portfolio.example/demo",
            "repository_url": None,
        },
        update_data={
            "title": "  Updated project  ",
            "description": "  Updated project description.  ",
            "technologies": "   ",
            "project_url": "",
            "repository_url": "  https://github.com/example/updated  ",
        },
        updated_fields={
            "title": "Updated project",
            "description": "Updated project description.",
            "technologies": None,
            "project_url": None,
            "repository_url": "https://github.com/example/updated",
        },
        invalid_data={
            "title": "Unsafe project",
            "description": "Must not be persisted.",
            "technologies": "Python",
            "project_url": "javascript:alert(1)",
            "repository_url": "",
        },
    ),
    ResourceCase(
        model=ExternalLink,
        resource="link",
        context_name="link",
        initial_fields={
            "label": "Original link",
            "url": "https://original.example/profile",
        },
        create_data={
            "label": "  GitHub  ",
            "url": "  https://github.com/ada  ",
        },
        created_fields={
            "label": "GitHub",
            "url": "https://github.com/ada",
        },
        update_data={
            "label": "  LinkedIn  ",
            "url": "  https://www.linkedin.com/in/ada  ",
        },
        updated_fields={
            "label": "LinkedIn",
            "url": "https://www.linkedin.com/in/ada",
        },
        invalid_data={"label": "Unsafe", "url": "javascript:alert(1)"},
    ),
)


def authenticate(client: TestClient, user: User) -> None:
    """Authenticate a test browser without exercising unrelated login behavior."""
    # Match the domain/path TestClient assigns to a real ``Set-Cookie`` response
    # so a renewed token replaces this cookie instead of creating a test-only
    # duplicate with the same name.
    client.cookies.set(
        "access_token",
        create_access_token({"sub": user.mail}),
        domain="testserver.local",
        path="/",
    )


def persist_resource(
    session: Session,
    case: ResourceCase,
    user_id: int,
    fields: dict[str, Any] | None = None,
) -> SQLModel:
    """Persist one resource using the case's valid baseline values."""
    record = case.model(**(fields or case.initial_fields), user_id=user_id)
    session.add(record)
    session.commit()
    session.refresh(record)
    return record


def assert_record_fields(record: SQLModel, expected: dict[str, Any]) -> None:
    for attribute, value in expected.items():
        assert getattr(record, attribute) == value


def test_profile_edit_routes_redirect_anonymous_users(client: TestClient) -> None:
    responses = (
        client.get("/profil/edit", follow_redirects=False),
        client.post(
            "/profil/edit",
            data=PROFILE_DATA,
            follow_redirects=False,
        ),
    )

    assert all(response.status_code == 303 for response in responses)
    assert all(response.headers["location"] == "/login" for response in responses)


def test_profile_edit_form_displays_the_current_account(
    client: TestClient,
    session: Session,
    user_factory: Callable[..., User],
) -> None:
    user = user_factory(mail="edit-form@example.com")
    user.bio = "Current biography"
    session.add(user)
    session.commit()
    authenticate(client, user)

    response = client.get("/profil/edit")

    assert response.status_code == 200
    assert response.context["user"].id == user.id
    assert response.context["form_values"] == {}
    assert "edit-form@example.com" in response.text
    assert "Current biography" in response.text


def test_profile_edit_rejects_a_missing_csrf_token_without_changing_the_user(
    client: TestClient,
    session: Session,
    user_factory: Callable[..., User],
) -> None:
    user = user_factory(mail="profile-csrf@example.com")
    authenticate(client, user)

    response = client.post(
        "/profil/edit",
        data={**PROFILE_DATA, "mail": "changed@example.com"},
        follow_redirects=False,
    )

    assert response.status_code == 403
    assert response.json() == {"detail": "Invalid or expired CSRF token"}
    session.refresh(user)
    assert user.mail == "profile-csrf@example.com"


def test_profile_edit_normalizes_data_and_refreshes_the_email_subject_jwt(
    client: TestClient,
    session: Session,
    user_factory: Callable[..., User],
    csrf_token: Callable[[str], str],
) -> None:
    user = user_factory(mail="old-address@example.com")
    assert user.id is not None
    user_id = user.id
    original_password_hash = user.hashed_password
    authenticate(client, user)
    token = csrf_token("/profil/edit")

    response = client.post(
        "/profil/edit",
        data={
            "csrf_token": token,
            "name": "  Hopper  ",
            "first_name": "  Grace  ",
            "birth_date": "1906-12-09",
            "mail": "  GRACE.HOPPER@Example.COM  ",
            "phone": "+33 6 12 34 56 78",
            "bio": "  Compiler pioneer.  ",
        },
        follow_redirects=False,
    )

    assert response.status_code == 303
    assert response.headers["location"] == "/profil"
    cookie_header = response.headers["set-cookie"]
    assert "access_token=" in cookie_header
    assert "HttpOnly" in cookie_header
    assert "SameSite=lax" in cookie_header

    refreshed_token = client.cookies.get("access_token")
    assert refreshed_token is not None
    assert decode_access_token(refreshed_token)["sub"] == "grace.hopper@example.com"

    session.expire_all()
    updated_user = session.get(User, user_id)
    assert updated_user is not None
    assert updated_user.name == "Hopper"
    assert updated_user.first_name == "Grace"
    assert updated_user.birth_date == date(1906, 12, 9)
    assert updated_user.mail == "grace.hopper@example.com"
    assert updated_user.phone == "+33612345678"
    assert updated_user.bio == "Compiler pioneer."
    assert updated_user.hashed_password == original_password_hash

    profile_response = client.get("/profil", follow_redirects=False)
    assert profile_response.status_code == 200
    assert "grace.hopper@example.com" in profile_response.text


def test_profile_edit_can_clear_an_existing_biography(
    client: TestClient,
    session: Session,
    user_factory: Callable[..., User],
    csrf_token: Callable[[str], str],
) -> None:
    user = user_factory(mail="clear-bio@example.com")
    user.bio = "Biography to remove"
    session.add(user)
    session.commit()
    authenticate(client, user)
    token = csrf_token("/profil/edit")

    response = client.post(
        "/profil/edit",
        data={
            **PROFILE_DATA,
            "mail": user.mail,
            "bio": "   ",
            "csrf_token": token,
        },
        follow_redirects=False,
    )

    assert response.status_code == 303
    session.refresh(user)
    assert user.bio is None


@pytest.mark.parametrize(
    ("field", "value", "expected_error"),
    [
        pytest.param("name", "   ", "Name is required.", id="blank-name"),
        pytest.param(
            "first_name",
            "x" * 101,
            "First name must contain at most 100 characters.",
            id="long-first-name",
        ),
        pytest.param(
            "birth_date",
            date.today().isoformat(),
            "Birth date must be in the past.",
            id="future-birth-date",
        ),
        pytest.param(
            "mail",
            "not-an-email",
            "Please enter a valid email address.",
            id="invalid-email",
        ),
        pytest.param(
            "phone",
            "call-me",
            "Please enter a valid phone number.",
            id="invalid-phone",
        ),
        pytest.param(
            "bio",
            "x" * 3001,
            "Biography must contain at most 3000 characters.",
            id="long-biography",
        ),
    ],
)
def test_profile_edit_returns_validation_errors_without_partial_updates(
    client: TestClient,
    session: Session,
    user_factory: Callable[..., User],
    csrf_token: Callable[[str], str],
    field: str,
    value: str,
    expected_error: str,
) -> None:
    user = user_factory(mail=f"invalid-{field}@example.com")
    assert user.id is not None
    user_id = user.id
    authenticate(client, user)
    token = csrf_token("/profil/edit")
    form_data = {**PROFILE_DATA, "mail": user.mail, field: value}

    response = client.post(
        "/profil/edit",
        data={"csrf_token": token, **form_data},
        follow_redirects=False,
    )

    assert response.status_code == 400
    assert expected_error in response.text
    assert response.context["form_values"] == form_data
    session.expire_all()
    unchanged_user = session.get(User, user_id)
    assert unchanged_user is not None
    assert unchanged_user.name == "Lovelace"
    assert unchanged_user.mail == f"invalid-{field}@example.com"


def test_profile_edit_rejects_another_accounts_normalized_email(
    client: TestClient,
    session: Session,
    user_factory: Callable[..., User],
    csrf_token: Callable[[str], str],
) -> None:
    owner = user_factory(mail="profile-owner@example.com")
    user_factory(mail="already-used@example.com")
    authenticate(client, owner)
    token = csrf_token("/profil/edit")

    response = client.post(
        "/profil/edit",
        data={
            **PROFILE_DATA,
            "mail": "  ALREADY-USED@EXAMPLE.COM  ",
            "csrf_token": token,
        },
        follow_redirects=False,
    )

    assert response.status_code == 409
    assert "An account already exists with this email address." in response.text
    session.refresh(owner)
    assert owner.mail == "profile-owner@example.com"


def test_profile_edit_rolls_back_a_concurrent_email_conflict(
    client: TestClient,
    session: Session,
    user_factory: Callable[..., User],
    csrf_token: Callable[[str], str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    user = user_factory(mail="concurrent-profile@example.com")
    assert user.id is not None
    user_id = user.id
    authenticate(client, user)
    token = csrf_token("/profil/edit")
    rollback_calls = 0
    original_rollback = Session.rollback

    def raise_unique_conflict(database_session: Session) -> None:
        raise IntegrityError(
            "UPDATE user SET mail = ?",
            {},
            RuntimeError("simulated concurrent unique conflict"),
        )

    def record_rollback(database_session: Session) -> None:
        nonlocal rollback_calls
        rollback_calls += 1
        original_rollback(database_session)

    monkeypatch.setattr(Session, "commit", raise_unique_conflict)
    monkeypatch.setattr(Session, "rollback", record_rollback)

    response = client.post(
        "/profil/edit",
        data={
            **PROFILE_DATA,
            "mail": "concurrent-new@example.com",
            "csrf_token": token,
        },
        follow_redirects=False,
    )

    assert response.status_code == 409
    assert rollback_calls == 1
    session.expire_all()
    unchanged_user = session.get(User, user_id)
    assert unchanged_user is not None
    assert unchanged_user.mail == "concurrent-profile@example.com"


@pytest.mark.parametrize("case", RESOURCE_CASES, ids=lambda case: case.resource)
def test_owned_content_routes_redirect_anonymous_users(
    client: TestClient,
    case: ResourceCase,
) -> None:
    responses = (
        client.get(f"/profil/{case.resource}", follow_redirects=False),
        client.post(
            f"/profil/{case.resource}",
            data=case.create_data,
            follow_redirects=False,
        ),
        client.get(
            f"/profil/{case.resource}/edit/999",
            follow_redirects=False,
        ),
        client.post(
            f"/profil/{case.resource}/edit/999",
            data=case.update_data,
            follow_redirects=False,
        ),
        client.post(
            f"/profil/{case.resource}/delete/999",
            follow_redirects=False,
        ),
    )

    assert all(response.status_code == 303 for response in responses)
    assert all(response.headers["location"] == "/login" for response in responses)


@pytest.mark.parametrize("case", RESOURCE_CASES, ids=lambda case: case.resource)
def test_owned_content_forms_show_only_records_owned_by_the_current_user(
    client: TestClient,
    session: Session,
    user_factory: Callable[..., User],
    case: ResourceCase,
) -> None:
    owner = user_factory(mail=f"form-owner-{case.resource}@example.com")
    other = user_factory(mail=f"form-other-{case.resource}@example.com")
    assert owner.id is not None
    assert other.id is not None
    owned_record = persist_resource(session, case, owner.id)
    foreign_record = persist_resource(session, case, other.id)
    assert owned_record.id is not None
    assert foreign_record.id is not None
    authenticate(client, owner)

    create_page = client.get(f"/profil/{case.resource}")
    edit_page = client.get(
        f"/profil/{case.resource}/edit/{owned_record.id}",
        follow_redirects=False,
    )
    foreign_page = client.get(
        f"/profil/{case.resource}/edit/{foreign_record.id}",
        follow_redirects=False,
    )
    missing_page = client.get(
        f"/profil/{case.resource}/edit/999999",
        follow_redirects=False,
    )

    assert create_page.status_code == 200
    assert create_page.context[case.context_name] is None
    assert create_page.context["form_values"] == {}
    assert edit_page.status_code == 200
    assert edit_page.context[case.context_name].id == owned_record.id
    assert edit_page.context["form_values"] == {}
    assert foreign_page.status_code == 303
    assert foreign_page.headers["location"] == "/profil"
    assert missing_page.status_code == 303
    assert missing_page.headers["location"] == "/profil"


@pytest.mark.parametrize("case", RESOURCE_CASES, ids=lambda case: case.resource)
def test_owned_content_mutations_require_csrf_tokens(
    client: TestClient,
    session: Session,
    user_factory: Callable[..., User],
    case: ResourceCase,
) -> None:
    owner = user_factory(mail=f"csrf-owner-{case.resource}@example.com")
    assert owner.id is not None
    record = persist_resource(session, case, owner.id)
    assert record.id is not None
    authenticate(client, owner)

    responses = (
        client.post(
            f"/profil/{case.resource}",
            data=case.create_data,
            follow_redirects=False,
        ),
        client.post(
            f"/profil/{case.resource}/edit/{record.id}",
            data=case.update_data,
            follow_redirects=False,
        ),
        client.post(
            f"/profil/{case.resource}/delete/{record.id}",
            follow_redirects=False,
        ),
    )

    assert all(response.status_code == 403 for response in responses)
    assert all(
        response.json() == {"detail": "Invalid or expired CSRF token"}
        for response in responses
    )
    session.expire_all()
    assert session.get(case.model, record.id) is not None
    assert len(session.exec(select(case.model)).all()) == 1


@pytest.mark.parametrize("case", RESOURCE_CASES, ids=lambda case: case.resource)
def test_owner_can_create_update_and_delete_sprint2_content(
    client: TestClient,
    session: Session,
    user_factory: Callable[..., User],
    csrf_token: Callable[[str], str],
    case: ResourceCase,
) -> None:
    owner = user_factory(mail=f"lifecycle-{case.resource}@example.com")
    assert owner.id is not None
    authenticate(client, owner)
    token = csrf_token(f"/profil/{case.resource}")

    create_response = client.post(
        f"/profil/{case.resource}",
        data={"csrf_token": token, **case.create_data},
        follow_redirects=False,
    )

    assert create_response.status_code == 303
    assert create_response.headers["location"] == "/profil"
    records = session.exec(select(case.model)).all()
    assert len(records) == 1
    record = records[0]
    assert record.id is not None
    assert record.user_id == owner.id
    assert_record_fields(record, case.created_fields)

    update_response = client.post(
        f"/profil/{case.resource}/edit/{record.id}",
        data={"csrf_token": token, **case.update_data},
        follow_redirects=False,
    )

    assert update_response.status_code == 303
    assert update_response.headers["location"] == "/profil"
    session.refresh(record)
    assert_record_fields(record, case.updated_fields)

    record_id = record.id
    delete_response = client.post(
        f"/profil/{case.resource}/delete/{record_id}",
        data={"csrf_token": token},
        follow_redirects=False,
    )

    assert delete_response.status_code == 303
    assert delete_response.headers["location"] == "/profil"
    session.expire_all()
    assert session.get(case.model, record_id) is None


@pytest.mark.parametrize("case", RESOURCE_CASES, ids=lambda case: case.resource)
def test_owned_content_validation_preserves_submitted_and_persisted_values(
    client: TestClient,
    session: Session,
    user_factory: Callable[..., User],
    csrf_token: Callable[[str], str],
    case: ResourceCase,
) -> None:
    owner = user_factory(mail=f"validation-{case.resource}@example.com")
    assert owner.id is not None
    authenticate(client, owner)
    token = csrf_token(f"/profil/{case.resource}")

    create_response = client.post(
        f"/profil/{case.resource}",
        data={"csrf_token": token, **case.invalid_data},
        follow_redirects=False,
    )

    assert create_response.status_code == 400
    assert create_response.context[case.context_name] is None
    assert create_response.context["form_values"] == case.invalid_data
    assert session.exec(select(case.model)).all() == []

    record = persist_resource(session, case, owner.id)
    assert record.id is not None
    update_response = client.post(
        f"/profil/{case.resource}/edit/{record.id}",
        data={"csrf_token": token, **case.invalid_data},
        follow_redirects=False,
    )

    assert update_response.status_code == 400
    assert update_response.context[case.context_name].id == record.id
    assert update_response.context["form_values"] == case.invalid_data
    session.refresh(record)
    assert_record_fields(record, case.initial_fields)


@pytest.mark.parametrize("case", RESOURCE_CASES, ids=lambda case: case.resource)
def test_another_user_cannot_update_or_delete_sprint2_content(
    client: TestClient,
    session: Session,
    user_factory: Callable[..., User],
    csrf_token: Callable[[str], str],
    case: ResourceCase,
) -> None:
    owner = user_factory(mail=f"content-owner-{case.resource}@example.com")
    attacker = user_factory(mail=f"content-attacker-{case.resource}@example.com")
    assert owner.id is not None
    record = persist_resource(session, case, owner.id)
    assert record.id is not None
    record_id = record.id
    authenticate(client, attacker)
    token = csrf_token(f"/profil/{case.resource}")

    responses = (
        client.post(
            f"/profil/{case.resource}/edit/{record_id}",
            data={"csrf_token": token, **case.update_data},
            follow_redirects=False,
        ),
        client.post(
            f"/profil/{case.resource}/edit/999999",
            data={"csrf_token": token, **case.update_data},
            follow_redirects=False,
        ),
        client.post(
            f"/profil/{case.resource}/delete/{record_id}",
            data={"csrf_token": token},
            follow_redirects=False,
        ),
        client.post(
            f"/profil/{case.resource}/delete/999999",
            data={"csrf_token": token},
            follow_redirects=False,
        ),
    )

    assert all(response.status_code == 303 for response in responses)
    assert all(response.headers["location"] == "/profil" for response in responses)
    session.expire_all()
    preserved_record = session.get(case.model, record_id)
    assert preserved_record is not None
    assert_record_fields(preserved_record, case.initial_fields)


def test_private_and_public_profiles_isolate_all_sprint2_content(
    client: TestClient,
    session: Session,
    user_factory: Callable[..., User],
) -> None:
    owner = user_factory(mail="aggregate-owner@example.com", first_name="VisibleOwner")
    other = user_factory(mail="aggregate-other@example.com", first_name="HiddenOther")
    assert owner.id is not None
    assert other.id is not None
    owner.bio = "Visible biography"
    other.bio = "Hidden biography"
    session.add(owner)
    session.add(other)
    session.add_all(
        [
            Skill(name="Visible skill", level=5, user_id=owner.id),
            Skill(name="Hidden skill", level=1, user_id=other.id),
            Project(
                title="Visible project",
                description="Visible project description",
                technologies="FastAPI",
                project_url="https://visible.example/demo",
                repository_url=None,
                user_id=owner.id,
            ),
            Project(
                title="Hidden project",
                description="Hidden project description",
                technologies=None,
                project_url=None,
                repository_url=None,
                user_id=other.id,
            ),
            ExternalLink(
                label="Visible link",
                url="https://visible.example/profile",
                user_id=owner.id,
            ),
            ExternalLink(
                label="Hidden link",
                url="https://hidden.example/profile",
                user_id=other.id,
            ),
        ]
    )
    session.commit()
    authenticate(client, owner)

    private_response = client.get("/profil")
    public_response = client.get(f"/portfolio/{owner.id}")

    for response in (private_response, public_response):
        assert response.status_code == 200
        assert [item.name for item in response.context["skills"]] == ["Visible skill"]
        assert [item.title for item in response.context["projects"]] == [
            "Visible project"
        ]
        assert [item.label for item in response.context["links"]] == ["Visible link"]
        assert "Visible biography" in response.text
        assert "Visible skill" in response.text
        assert "Visible project" in response.text
        assert "Visible link" in response.text
        assert "Hidden biography" not in response.text
        assert "Hidden skill" not in response.text
        assert "Hidden project" not in response.text
        assert "Hidden link" not in response.text


def test_normalized_header_is_shared_by_public_pages(
    client: TestClient,
    user_factory: Callable[..., User],
) -> None:
    user = user_factory(mail="public-header@example.com")
    paths = ("/", "/login", "/create_user", f"/portfolio/{user.id}")

    for path in paths:
        response = client.get(path)
        assert response.status_code == 200
        assert response.text.count('<header class="site-header">') == 1
        assert 'class="site-header__brand" href="/"' in response.text
        assert 'aria-label="Main navigation"' in response.text
        assert 'href="/login"' in response.text
        assert 'href="/create_user"' in response.text
        assert 'class="site-header__logout"' not in response.text


def test_normalized_header_keeps_private_navigation_and_csrf_logout(
    authenticated_client: TestClient,
) -> None:
    paths = (
        "/profil",
        "/profil/edit",
        "/profil/experience",
        "/profil/education",
        "/profil/skill",
        "/profil/project",
        "/profil/link",
    )

    for path in paths:
        response = authenticated_client.get(path)
        assert response.status_code == 200
        assert response.text.count('<header class="site-header">') == 1
        assert 'class="site-header__brand" href="/"' in response.text
        assert 'href="/profil"' in response.text
        assert 'class="site-header__logout" action="/logout" method="post"' in response.text
        assert 'name="csrf_token"' in response.text
