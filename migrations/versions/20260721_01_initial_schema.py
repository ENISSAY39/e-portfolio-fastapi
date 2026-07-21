"""Create or adopt the initial portfolio schema.

Revision ID: 20260721_01
Revises:
Create Date: 2026-07-21
"""

from __future__ import annotations

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "20260721_01"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _has_index(
    inspector: sa.Inspector,
    table_name: str,
    columns: list[str],
    *,
    unique: bool | None = None,
) -> bool:
    expected_columns = tuple(columns)
    for index in inspector.get_indexes(table_name):
        if tuple(index.get("column_names") or ()) != expected_columns:
            continue
        if unique is None or bool(index.get("unique")) is unique:
            return True

    if unique:
        for constraint in inspector.get_unique_constraints(table_name):
            if tuple(constraint.get("column_names") or ()) == expected_columns:
                return True
    return False


def _normalize_existing_emails(bind: sa.Connection) -> None:
    metadata = sa.MetaData()
    user_table = sa.Table("user", metadata, autoload_with=bind)
    normalized_mail = sa.func.lower(sa.func.trim(user_table.c.mail))

    duplicate = bind.execute(
        sa.select(normalized_mail, sa.func.count())
        .group_by(normalized_mail)
        .having(sa.func.count() > 1)
        .limit(1)
    ).first()
    if duplicate:
        raise RuntimeError(
            "Cannot enforce unique normalized emails: duplicate user emails exist."
        )

    bind.execute(user_table.update().values(mail=normalized_mail))


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    tables = set(inspector.get_table_names())

    if "user" not in tables:
        op.create_table(
            "user",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("name", sa.String(), nullable=False),
            sa.Column("first_name", sa.String(), nullable=False),
            sa.Column("birth_date", sa.Date(), nullable=False),
            sa.Column("mail", sa.String(), nullable=False),
            sa.Column("phone", sa.String(), nullable=False),
            sa.Column("hashed_password", sa.String(), nullable=False),
            sa.PrimaryKeyConstraint("id"),
        )
        op.create_index("ix_user_mail", "user", ["mail"], unique=True)
    else:
        _normalize_existing_emails(bind)
        inspector = sa.inspect(bind)
        if not _has_index(inspector, "user", ["mail"], unique=True):
            op.create_index("ix_user_mail", "user", ["mail"], unique=True)

    inspector = sa.inspect(bind)
    tables = set(inspector.get_table_names())

    if "experience" not in tables:
        op.create_table(
            "experience",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("title", sa.String(), nullable=False),
            sa.Column("date_start", sa.DateTime(), nullable=False),
            sa.Column("date_end", sa.DateTime(), nullable=False),
            sa.Column("description", sa.String(), nullable=False),
            sa.Column("company", sa.String(), nullable=False),
            sa.Column("user_id", sa.Integer(), nullable=False),
            sa.CheckConstraint(
                "date_end >= date_start", name="ck_experience_date_order"
            ),
            sa.ForeignKeyConstraint(["user_id"], ["user.id"]),
            sa.PrimaryKeyConstraint("id"),
        )
        op.create_index(
            "ix_experience_user_id", "experience", ["user_id"], unique=False
        )
    else:
        inspector = sa.inspect(bind)
        if not _has_index(inspector, "experience", ["user_id"]):
            op.create_index(
                "ix_experience_user_id", "experience", ["user_id"], unique=False
            )
        check_names = {
            check.get("name") for check in inspector.get_check_constraints("experience")
        }
        if (
            bind.dialect.name != "sqlite"
            and "ck_experience_date_order" not in check_names
        ):
            op.create_check_constraint(
                "ck_experience_date_order",
                "experience",
                "date_end >= date_start",
            )

    inspector = sa.inspect(bind)
    tables = set(inspector.get_table_names())

    if "education" not in tables:
        op.create_table(
            "education",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("school_name", sa.String(), nullable=False),
            sa.Column("date_start", sa.DateTime(), nullable=False),
            sa.Column("date_end", sa.DateTime(), nullable=False),
            sa.Column("description", sa.String(), nullable=False),
            sa.Column("major", sa.String(), nullable=False),
            sa.Column("user_id", sa.Integer(), nullable=False),
            sa.CheckConstraint(
                "date_end >= date_start", name="ck_education_date_order"
            ),
            sa.ForeignKeyConstraint(["user_id"], ["user.id"]),
            sa.PrimaryKeyConstraint("id"),
        )
        op.create_index(
            "ix_education_user_id", "education", ["user_id"], unique=False
        )
    else:
        inspector = sa.inspect(bind)
        if not _has_index(inspector, "education", ["user_id"]):
            op.create_index(
                "ix_education_user_id", "education", ["user_id"], unique=False
            )
        check_names = {
            check.get("name") for check in inspector.get_check_constraints("education")
        }
        if bind.dialect.name != "sqlite" and "ck_education_date_order" not in check_names:
            op.create_check_constraint(
                "ck_education_date_order",
                "education",
                "date_end >= date_start",
            )


def downgrade() -> None:
    op.drop_index("ix_education_user_id", table_name="education")
    op.drop_table("education")
    op.drop_index("ix_experience_user_id", table_name="experience")
    op.drop_table("experience")
    op.drop_index("ix_user_mail", table_name="user")
    op.drop_table("user")
