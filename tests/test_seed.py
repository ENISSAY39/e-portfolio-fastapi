"""Regression tests for safe, idempotent demonstration-data seeding."""

from collections import Counter
from datetime import date, datetime

import pytest
from sqlalchemy import Engine
from sqlmodel import Session, select

import seed as seed_module
from schemas.Education import Education
from schemas.Experiences import Experience
from schemas.User import User


TEST_PASSWORD_HASH = "test-only-hashed-demo-password"


def _isolate_seed(
    monkeypatch: pytest.MonkeyPatch,
    test_engine: Engine,
) -> list[str]:
    """Point the seed module at the temporary database and record hashing."""
    password_inputs: list[str] = []

    def record_password_hash(password: str) -> str:
        password_inputs.append(password)
        return TEST_PASSWORD_HASH

    monkeypatch.setattr(seed_module, "engine", test_engine)
    monkeypatch.setattr(seed_module, "hash_password", record_password_hash)
    return password_inputs


def test_seed_populates_an_empty_database_idempotently(
    test_engine: Engine,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    password_inputs = _isolate_seed(monkeypatch, test_engine)

    seed_module.seed()

    assert capsys.readouterr().out == (
        "Seed synchronized: "
        "10 user(s), 10 education(s), 20 experience(s) created\n"
    )
    assert password_inputs == ["test"]

    with Session(test_engine) as session:
        users = session.exec(select(User)).all()
        educations = session.exec(select(Education)).all()
        experiences = session.exec(select(Experience)).all()

        assert {user.mail for user in users} == {
            f"user{index}@mail.com" for index in range(1, 11)
        }
        assert all(user.hashed_password == TEST_PASSWORD_HASH for user in users)
        assert all(user.hashed_password != "test" for user in users)

        user_ids = {user.id for user in users}
        assert None not in user_ids
        assert Counter(education.user_id for education in educations) == {
            user_id: 1 for user_id in user_ids
        }
        assert Counter(experience.user_id for experience in experiences) == {
            user_id: 2 for user_id in user_ids
        }

        first_user_ids = {user.mail: user.id for user in users}
        first_education_ids = {education.id for education in educations}
        first_experience_ids = {experience.id for experience in experiences}

    seed_module.seed()

    assert capsys.readouterr().out == (
        "Seed synchronized: "
        "0 user(s), 0 education(s), 0 experience(s) created\n"
    )
    assert password_inputs == ["test"]

    with Session(test_engine) as session:
        users = session.exec(select(User)).all()
        educations = session.exec(select(Education)).all()
        experiences = session.exec(select(Experience)).all()

        assert {user.mail: user.id for user in users} == first_user_ids
        assert {education.id for education in educations} == first_education_ids
        assert {experience.id for experience in experiences} == first_experience_ids


def test_seed_preserves_existing_records_and_adds_only_missing_demo_data(
    test_engine: Engine,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    with Session(test_engine) as session:
        existing_demo_user = User(
            name="Keep this name",
            first_name="Keep this first name",
            birth_date=date(1980, 1, 1),
            mail="user1@mail.com",
            phone="0611111111",
            hashed_password="existing-password-hash",
        )
        unrelated_user = User(
            name="Real",
            first_name="User",
            birth_date=date(1990, 2, 2),
            mail="real.user@example.com",
            phone="0622222222",
            hashed_password="real-user-password-hash",
        )
        session.add(existing_demo_user)
        session.add(unrelated_user)
        session.flush()

        assert existing_demo_user.id is not None
        existing_demo_user_id = existing_demo_user.id
        unrelated_user_id = unrelated_user.id

        session.add(
            Education(
                school_name="University 1",
                date_start=datetime(2010, 9, 1),
                date_end=datetime(2014, 6, 1),
                description="Keep this education",
                major="Existing major",
                user_id=existing_demo_user_id,
            )
        )
        session.add(
            Experience(
                title="Intern",
                date_start=datetime(2019, 1, 1),
                date_end=datetime(2019, 6, 1),
                description="Keep this experience",
                company="Company A",
                user_id=existing_demo_user_id,
            )
        )
        session.commit()

    password_inputs = _isolate_seed(monkeypatch, test_engine)

    seed_module.seed()

    assert capsys.readouterr().out == (
        "Seed synchronized: "
        "9 user(s), 9 education(s), 19 experience(s) created\n"
    )
    assert password_inputs == ["test"]

    with Session(test_engine) as session:
        users = session.exec(select(User)).all()
        educations = session.exec(select(Education)).all()
        experiences = session.exec(select(Experience)).all()

        assert len(users) == 11
        assert len(educations) == 10
        assert len(experiences) == 20

        preserved_demo_user = session.exec(
            select(User).where(User.id == existing_demo_user_id)
        ).one()
        assert preserved_demo_user.name == "Keep this name"
        assert preserved_demo_user.first_name == "Keep this first name"
        assert preserved_demo_user.birth_date == date(1980, 1, 1)
        assert preserved_demo_user.phone == "0611111111"
        assert preserved_demo_user.hashed_password == "existing-password-hash"

        preserved_education = session.exec(
            select(Education).where(
                Education.user_id == existing_demo_user_id,
                Education.school_name == "University 1",
            )
        ).one()
        assert preserved_education.description == "Keep this education"
        assert preserved_education.major == "Existing major"

        demo_experiences = session.exec(
            select(Experience).where(Experience.user_id == existing_demo_user_id)
        ).all()
        assert {(experience.title, experience.company) for experience in demo_experiences} == {
            ("Intern", "Company A"),
            ("Engineer", "Company B"),
        }
        preserved_experience = next(
            experience
            for experience in demo_experiences
            if experience.title == "Intern"
        )
        assert preserved_experience.description == "Keep this experience"

        preserved_unrelated_user = session.exec(
            select(User).where(User.id == unrelated_user_id)
        ).one()
        assert preserved_unrelated_user.mail == "real.user@example.com"
        assert preserved_unrelated_user.hashed_password == "real-user-password-hash"


def test_seed_repairs_only_missing_related_demo_records(
    test_engine: Engine,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    password_inputs = _isolate_seed(monkeypatch, test_engine)
    seed_module.seed()
    capsys.readouterr()

    with Session(test_engine) as session:
        target_user = session.exec(
            select(User).where(User.mail == "user5@mail.com")
        ).one()
        education_to_remove = session.exec(
            select(Education).where(Education.user_id == target_user.id)
        ).one()
        experience_to_remove = session.exec(
            select(Experience).where(
                Experience.user_id == target_user.id,
                Experience.title == "Engineer",
                Experience.company == "Company B",
            )
        ).one()

        preserved_user_ids = {user.id for user in session.exec(select(User)).all()}
        preserved_education_ids = {
            education.id
            for education in session.exec(select(Education)).all()
            if education.id != education_to_remove.id
        }
        preserved_experience_ids = {
            experience.id
            for experience in session.exec(select(Experience)).all()
            if experience.id != experience_to_remove.id
        }

        session.delete(education_to_remove)
        session.delete(experience_to_remove)
        session.commit()

    seed_module.seed()

    assert capsys.readouterr().out == (
        "Seed synchronized: "
        "0 user(s), 1 education(s), 1 experience(s) created\n"
    )
    assert password_inputs == ["test"]

    with Session(test_engine) as session:
        users = session.exec(select(User)).all()
        educations = session.exec(select(Education)).all()
        experiences = session.exec(select(Experience)).all()

        assert {user.id for user in users} == preserved_user_ids
        assert len(educations) == 10
        assert len(experiences) == 20
        assert preserved_education_ids < {education.id for education in educations}
        assert preserved_experience_ids < {
            experience.id for experience in experiences
        }
