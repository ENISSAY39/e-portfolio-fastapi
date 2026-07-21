"""Integration tests for public portfolio discovery and search pagination."""

from datetime import date

import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session

from schemas.User import User


def _create_public_users(session: Session, names: list[str]) -> None:
    """Persist lightweight public accounts without doing irrelevant password work."""
    for index, name in enumerate(names):
        session.add(
            User(
                name=name,
                first_name=f"Public{index:02d}",
                birth_date=date(1990, 1, 1),
                mail=f"public{index:02d}@example.com",
                phone=f"060000{index:04d}",
                hashed_password="unused-test-password-hash",
            )
        )
    session.commit()


def _assert_pagination_link(html: str, target: str) -> None:
    """Accept equivalent HTML serializations of an ampersand in a link."""
    escaped_target = target.replace("&", "&amp;")
    assert f'href="{target}"' in html or f'href="{escaped_target}"' in html


def test_home_renders_an_empty_directory_without_pagination(
    client: TestClient,
) -> None:
    response = client.get("/")

    assert response.status_code == 200
    assert response.text.count('href="/portfolio/') == 0
    assert 'class="pagination"' not in response.text
    assert response.context["users"] == []
    assert response.context["current_page"] == 1
    assert response.context["total_pages"] == 0
    assert response.context["has_previous"] is False
    assert response.context["has_next"] is False


@pytest.mark.parametrize(
    (
        "requested_page",
        "expected_page",
        "expected_user_count",
        "has_previous",
        "has_next",
    ),
    [
        pytest.param(1, 1, 10, False, True, id="first-page"),
        pytest.param(2, 2, 2, True, False, id="last-page"),
        pytest.param(0, 1, 10, False, True, id="below-lower-bound"),
        pytest.param(999, 2, 2, True, False, id="above-upper-bound"),
    ],
)
def test_home_paginates_and_clamps_page_numbers(
    client: TestClient,
    session: Session,
    requested_page: int,
    expected_page: int,
    expected_user_count: int,
    has_previous: bool,
    has_next: bool,
) -> None:
    _create_public_users(
        session,
        [f"Portfolio{index:02d}" for index in range(12)],
    )

    response = client.get("/", params={"page": requested_page})

    assert response.status_code == 200
    assert response.text.count('href="/portfolio/') == expected_user_count
    assert f"Page {expected_page} of 2" in response.text
    assert response.context["current_page"] == expected_page
    assert response.context["total_pages"] == 2
    assert response.context["has_previous"] is has_previous
    assert response.context["has_next"] is has_next

    if has_previous:
        _assert_pagination_link(response.text, f"?page={expected_page - 1}")
    else:
        assert "<button disabled>Previous</button>" in response.text

    if has_next:
        _assert_pagination_link(response.text, f"?page={expected_page + 1}")
    else:
        assert "<button disabled>Next</button>" in response.text


@pytest.mark.parametrize(
    (
        "requested_page",
        "expected_page",
        "expected_user_count",
        "has_previous",
        "has_next",
    ),
    [
        pytest.param(1, 1, 10, False, True, id="first-page"),
        pytest.param(2, 2, 2, True, False, id="last-page"),
        pytest.param(0, 1, 10, False, True, id="below-lower-bound"),
        pytest.param(999, 2, 2, True, False, id="above-upper-bound"),
    ],
)
def test_search_filters_paginates_and_preserves_the_query(
    client: TestClient,
    session: Session,
    requested_page: int,
    expected_page: int,
    expected_user_count: int,
    has_previous: bool,
    has_next: bool,
) -> None:
    _create_public_users(
        session,
        [f"Match{index:02d}" for index in range(12)]
        + ["Unrelated00", "Unrelated01"],
    )

    response = client.get(
        "/search",
        params={"query": "Match", "page": requested_page},
    )

    assert response.status_code == 200
    assert response.text.count('href="/portfolio/') == expected_user_count
    assert "Unrelated" not in response.text
    assert 'value="Match"' in response.text
    assert f"Page {expected_page} of 2" in response.text
    assert response.context["query"] == "Match"
    assert response.context["current_page"] == expected_page
    assert response.context["total_pages"] == 2
    assert response.context["has_previous"] is has_previous
    assert response.context["has_next"] is has_next

    if has_previous:
        _assert_pagination_link(
            response.text,
            f"?query=Match&page={expected_page - 1}",
        )
    else:
        assert "<button disabled>Previous</button>" in response.text

    if has_next:
        _assert_pagination_link(
            response.text,
            f"?query=Match&page={expected_page + 1}",
        )
    else:
        assert "<button disabled>Next</button>" in response.text


def test_search_renders_no_results_and_clamps_an_excessive_page(
    client: TestClient,
    session: Session,
) -> None:
    _create_public_users(session, ["Unrelated"])

    response = client.get(
        "/search",
        params={"query": "Absent", "page": 999},
    )

    assert response.status_code == 200
    assert response.text.count('href="/portfolio/') == 0
    assert 'value="Absent"' in response.text
    assert 'class="pagination"' not in response.text
    assert response.context["users"] == []
    assert response.context["query"] == "Absent"
    assert response.context["current_page"] == 1
    assert response.context["total_pages"] == 1
    assert response.context["has_previous"] is False
    assert response.context["has_next"] is False
