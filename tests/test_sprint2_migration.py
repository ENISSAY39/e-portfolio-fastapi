"""Regression test for the forward Sprint 2 Alembic migration."""

from __future__ import annotations

from pathlib import Path

from alembic import command
from alembic.config import Config
from sqlalchemy import URL, create_engine, inspect, text


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def test_sprint2_migration_preserves_users_and_matches_registered_metadata(
    tmp_path: Path,
) -> None:
    """Upgrade a real Sprint 1 schema, then ask Alembic for metadata drift."""
    database_path = tmp_path / "migration.db"
    engine = create_engine(URL.create("sqlite", database=str(database_path)))
    config = Config(str(PROJECT_ROOT / "alembic.ini"))

    try:
        with engine.begin() as connection:
            config.attributes["connection"] = connection
            command.upgrade(config, "20260721_01")
            connection.execute(
                text(
                    """
                    INSERT INTO user (
                        name,
                        first_name,
                        birth_date,
                        mail,
                        phone,
                        hashed_password
                    ) VALUES (
                        :name,
                        :first_name,
                        :birth_date,
                        :mail,
                        :phone,
                        :hashed_password
                    )
                    """
                ),
                {
                    "name": "Existing",
                    "first_name": "Account",
                    "birth_date": "1990-01-01",
                    "mail": "existing@example.com",
                    "phone": "0612345678",
                    "hashed_password": "existing-test-hash",
                },
            )

            command.upgrade(config, "head")

            inspector = inspect(connection)
            assert {"skill", "project", "external_link"} <= set(
                inspector.get_table_names()
            )

            user_columns = {
                column["name"]: column for column in inspector.get_columns("user")
            }
            assert user_columns["bio"]["nullable"] is True
            existing_user = connection.execute(
                text("SELECT mail, bio FROM user WHERE mail = :mail"),
                {"mail": "existing@example.com"},
            ).one()
            assert existing_user.mail == "existing@example.com"
            assert existing_user.bio is None

            for table_name in ("skill", "project", "external_link"):
                indexes = inspector.get_indexes(table_name)
                assert any(
                    index["column_names"] == ["user_id"] for index in indexes
                )
                foreign_keys = inspector.get_foreign_keys(table_name)
                assert any(
                    foreign_key["constrained_columns"] == ["user_id"]
                    and foreign_key["referred_table"] == "user"
                    and foreign_key["referred_columns"] == ["id"]
                    for foreign_key in foreign_keys
                )

            skill_checks = {
                constraint["name"]
                for constraint in inspector.get_check_constraints("skill")
            }
            assert "ck_skill_level_range" in skill_checks

            # This catches a forgotten model import in migrations/env.py or any
            # mismatch between the reviewed revision and SQLModel declarations.
            command.check(config)
    finally:
        engine.dispose()

