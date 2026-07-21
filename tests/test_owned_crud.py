"""Integration tests for authenticated, user-owned portfolio records."""

from collections.abc import Callable
from datetime import datetime
from typing import Any

import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session, select

from core.security import create_access_token
from schemas.Education import Education
from schemas.Experiences import Experience
from schemas.User import User


PortfolioModel = type[Experience] | type[Education]


RESOURCE_CASES = [
    pytest.param(
        Experience,
        "experience",
        {
            "title": "  Backend developer  ",
            "date_start": "2024-01-01",
            "date_end": "2024-06-30",
            "description": "  Built a FastAPI service.  ",
            "company": "  Example Corp  ",
        },
        {
            "title": "Senior backend developer",
            "date_start": "2024-07-01",
            "date_end": "2025-06-30",
            "description": "Led the API team.",
            "company": "New Example Corp",
        },
        "title",
        "Backend developer",
        "Senior backend developer",
        id="experience",
    ),
    pytest.param(
        Education,
        "education",
        {
            "school_name": "  EPF Engineering School  ",
            "date_start": "2022-09-01",
            "date_end": "2025-06-30",
            "description": "  Computer science curriculum.  ",
            "major": "  Software engineering  ",
        },
        {
            "school_name": "EPF Graduate School",
            "date_start": "2022-09-01",
            "date_end": "2026-06-30",
            "description": "Extended computer science curriculum.",
            "major": "Cloud engineering",
        },
        "school_name",
        "EPF Engineering School",
        "EPF Graduate School",
        id="education",
    ),
]


def authenticate(client: TestClient, mail: str) -> None:
    """Authenticate the test browser as the user identified by ``mail``."""
    client.cookies.set("access_token", create_access_token({"sub": mail}))


@pytest.mark.parametrize("resource", ["experience", "education"])
def test_owned_crud_pages_redirect_anonymous_users(
    client: TestClient,
    resource: str,
) -> None:
    response = client.get(f"/profil/{resource}", follow_redirects=False)

    assert response.status_code == 303
    assert response.headers["location"] == "/login"


@pytest.mark.parametrize(
    ("resource", "form_data"),
    [
        pytest.param(
            "experience",
            {
                "title": "Developer",
                "date_start": "2025-01-01",
                "date_end": "2025-12-31",
                "description": "Anonymous mutation",
                "company": "Example Corp",
            },
            id="experience",
        ),
        pytest.param(
            "education",
            {
                "school_name": "EPF",
                "date_start": "2025-01-01",
                "date_end": "2025-12-31",
                "description": "Anonymous mutation",
                "major": "Computer science",
            },
            id="education",
        ),
    ],
)
def test_owned_mutation_and_edit_routes_redirect_anonymous_users(
    client: TestClient,
    resource: str,
    form_data: dict[str, str],
) -> None:
    responses = (
        client.post(
            f"/profil/{resource}",
            data=form_data,
            follow_redirects=False,
        ),
        client.post(
            f"/profil/{resource}/delete/999",
            follow_redirects=False,
        ),
        client.get(
            f"/profil/{resource}/edit/999",
            follow_redirects=False,
        ),
        client.post(
            f"/profil/{resource}/edit/999",
            data=form_data,
            follow_redirects=False,
        ),
    )

    assert all(response.status_code == 303 for response in responses)
    assert all(response.headers["location"] == "/login" for response in responses)


@pytest.mark.parametrize(
    ("model", "resource", "form_data"),
    [
        pytest.param(
            Experience,
            "experience",
            {
                "title": "Developer",
                "date_start": "2025-01-01",
                "date_end": "2025-12-31",
                "description": "Protected mutation",
                "company": "Example Corp",
            },
            id="experience",
        ),
        pytest.param(
            Education,
            "education",
            {
                "school_name": "EPF",
                "date_start": "2025-01-01",
                "date_end": "2025-12-31",
                "description": "Protected mutation",
                "major": "Computer science",
            },
            id="education",
        ),
    ],
)
def test_owned_create_routes_reject_a_missing_csrf_token(
    client: TestClient,
    session: Session,
    user_factory: Callable[..., User],
    model: PortfolioModel,
    resource: str,
    form_data: dict[str, str],
) -> None:
    owner = user_factory(mail=f"csrf-{resource}@example.com")
    authenticate(client, owner.mail)

    response = client.post(
        f"/profil/{resource}",
        data=form_data,
        follow_redirects=False,
    )

    assert response.status_code == 403
    assert response.json() == {"detail": "Invalid or expired CSRF token"}
    assert session.exec(select(model)).all() == []


@pytest.mark.parametrize(
    (
        "model",
        "resource",
        "create_data",
        "update_data",
        "display_attribute",
        "created_display_value",
        "updated_display_value",
    ),
    RESOURCE_CASES,
)
def test_owner_can_create_update_and_delete_a_portfolio_record(
    client: TestClient,
    session: Session,
    user_factory: Callable[..., User],
    csrf_token: Callable[[str], str],
    model: PortfolioModel,
    resource: str,
    create_data: dict[str, str],
    update_data: dict[str, str],
    display_attribute: str,
    created_display_value: str,
    updated_display_value: str,
) -> None:
    owner = user_factory(mail=f"owner-{resource}@example.com")
    authenticate(client, owner.mail)
    token = csrf_token(path=f"/profil/{resource}")

    create_response = client.post(
        f"/profil/{resource}",
        data={"csrf_token": token, **create_data},
        follow_redirects=False,
    )

    assert create_response.status_code == 303
    assert create_response.headers["location"] == "/profil"
    records = session.exec(select(model)).all()
    assert len(records) == 1
    record = records[0]
    assert record.id is not None
    assert record.user_id == owner.id
    assert getattr(record, display_attribute) == created_display_value

    edit_page = client.get(
        f"/profil/{resource}/edit/{record.id}",
        follow_redirects=False,
    )
    assert edit_page.status_code == 200
    assert created_display_value in edit_page.text

    update_response = client.post(
        f"/profil/{resource}/edit/{record.id}",
        data={"csrf_token": token, **update_data},
        follow_redirects=False,
    )

    assert update_response.status_code == 303
    assert update_response.headers["location"] == "/profil"
    session.refresh(record)
    assert getattr(record, display_attribute) == updated_display_value

    record_id = record.id
    delete_response = client.post(
        f"/profil/{resource}/delete/{record_id}",
        data={"csrf_token": token},
        follow_redirects=False,
    )

    assert delete_response.status_code == 303
    assert delete_response.headers["location"] == "/profil"
    session.expire_all()
    assert session.get(model, record_id) is None


@pytest.mark.parametrize(
    ("resource", "form_data", "model"),
    [
        pytest.param(
            "experience",
            {
                "title": "Developer",
                "date_start": "2025-02-01",
                "date_end": "2025-01-31",
                "description": "Invalid date range",
                "company": "Example Corp",
            },
            Experience,
            id="experience",
        ),
        pytest.param(
            "education",
            {
                "school_name": "EPF",
                "date_start": "2025-02-01",
                "date_end": "2025-01-31",
                "description": "Invalid date range",
                "major": "Computer science",
            },
            Education,
            id="education",
        ),
    ],
)
def test_create_rejects_an_invalid_date_range_without_persisting(
    client: TestClient,
    session: Session,
    user_factory: Callable[..., User],
    csrf_token: Callable[[str], str],
    resource: str,
    form_data: dict[str, str],
    model: PortfolioModel,
) -> None:
    owner = user_factory(mail=f"validation-{resource}@example.com")
    authenticate(client, owner.mail)
    token = csrf_token(path=f"/profil/{resource}")

    response = client.post(
        f"/profil/{resource}",
        data={"csrf_token": token, **form_data},
        follow_redirects=False,
    )

    assert response.status_code == 400
    assert "End date must be after or equal to start date." in response.text
    assert session.exec(select(model)).all() == []


@pytest.mark.parametrize(
    (
        "model",
        "resource",
        "record_fields",
        "invalid_form_data",
        "display_attribute",
        "original_display_value",
    ),
    [
        pytest.param(
            Experience,
            "experience",
            {
                "title": "Original experience",
                "date_start": datetime(2024, 1, 1),
                "date_end": datetime(2024, 12, 31),
                "description": "Original description",
                "company": "Original company",
            },
            {
                "title": "Rejected experience",
                "date_start": "2025-02-01",
                "date_end": "2025-01-31",
                "description": "Rejected description",
                "company": "Rejected company",
            },
            "title",
            "Original experience",
            id="experience",
        ),
        pytest.param(
            Education,
            "education",
            {
                "school_name": "Original school",
                "date_start": datetime(2021, 9, 1),
                "date_end": datetime(2024, 6, 30),
                "description": "Original description",
                "major": "Original major",
            },
            {
                "school_name": "Rejected school",
                "date_start": "2025-02-01",
                "date_end": "2025-01-31",
                "description": "Rejected description",
                "major": "Rejected major",
            },
            "school_name",
            "Original school",
            id="education",
        ),
    ],
)
def test_update_rejects_an_invalid_date_range_without_changing_the_record(
    client: TestClient,
    session: Session,
    user_factory: Callable[..., User],
    csrf_token: Callable[[str], str],
    model: PortfolioModel,
    resource: str,
    record_fields: dict[str, Any],
    invalid_form_data: dict[str, str],
    display_attribute: str,
    original_display_value: str,
) -> None:
    owner = user_factory(mail=f"invalid-update-{resource}@example.com")
    record = model(**record_fields, user_id=owner.id)
    session.add(record)
    session.commit()
    session.refresh(record)
    assert record.id is not None

    authenticate(client, owner.mail)
    token = csrf_token(path=f"/profil/{resource}")

    response = client.post(
        f"/profil/{resource}/edit/{record.id}",
        data={"csrf_token": token, **invalid_form_data},
        follow_redirects=False,
    )

    assert response.status_code == 400
    assert "End date must be after or equal to start date." in response.text
    assert next(iter(invalid_form_data.values())) in response.text
    session.refresh(record)
    assert getattr(record, display_attribute) == original_display_value


@pytest.mark.parametrize(
    (
        "model",
        "resource",
        "form_data",
        "display_attribute",
        "original_display_value",
        "record_fields",
    ),
    [
        pytest.param(
            Experience,
            "experience",
            {
                "title": "Stolen experience",
                "date_start": "2025-01-01",
                "date_end": "2025-12-31",
                "description": "Must not be persisted",
                "company": "Attacker Corp",
            },
            "title",
            "Owner experience",
            {
                "title": "Owner experience",
                "date_start": datetime(2024, 1, 1),
                "date_end": datetime(2024, 12, 31),
                "description": "Private owner record",
                "company": "Owner Corp",
            },
            id="experience",
        ),
        pytest.param(
            Education,
            "education",
            {
                "school_name": "Stolen education",
                "date_start": "2025-01-01",
                "date_end": "2025-12-31",
                "description": "Must not be persisted",
                "major": "Attacker major",
            },
            "school_name",
            "Owner school",
            {
                "school_name": "Owner school",
                "date_start": datetime(2021, 9, 1),
                "date_end": datetime(2024, 6, 30),
                "description": "Private owner record",
                "major": "Owner major",
            },
            id="education",
        ),
    ],
)
def test_another_user_cannot_view_update_or_delete_owned_records(
    client: TestClient,
    session: Session,
    user_factory: Callable[..., User],
    csrf_token: Callable[[str], str],
    model: PortfolioModel,
    resource: str,
    form_data: dict[str, str],
    display_attribute: str,
    original_display_value: str,
    record_fields: dict[str, Any],
) -> None:
    owner = user_factory(mail=f"record-owner-{resource}@example.com")
    attacker = user_factory(mail=f"attacker-{resource}@example.com")
    record = model(**record_fields, user_id=owner.id)
    session.add(record)
    session.commit()
    session.refresh(record)
    assert record.id is not None
    record_id = record.id

    authenticate(client, attacker.mail)
    token = csrf_token(path=f"/profil/{resource}")

    edit_page = client.get(
        f"/profil/{resource}/edit/{record_id}",
        follow_redirects=False,
    )
    assert edit_page.status_code == 303
    assert edit_page.headers["location"] == "/profil"

    update_response = client.post(
        f"/profil/{resource}/edit/{record_id}",
        data={"csrf_token": token, **form_data},
        follow_redirects=False,
    )
    assert update_response.status_code == 303
    assert update_response.headers["location"] == "/profil"
    session.refresh(record)
    assert getattr(record, display_attribute) == original_display_value

    delete_response = client.post(
        f"/profil/{resource}/delete/{record_id}",
        data={"csrf_token": token},
        follow_redirects=False,
    )
    assert delete_response.status_code == 303
    assert delete_response.headers["location"] == "/profil"
    session.expire_all()
    assert session.get(model, record_id) is not None
