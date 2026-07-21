"""Create or adopt the initial portfolio schema.

Unlike a conventional initial revision that assumes an empty database, this
migration also supports databases created by the application's former
``SQLModel.metadata.create_all()`` startup behavior. Existing tables are
inspected, legacy emails are normalized, and only missing constraints or
indexes are added.

Revision ID: 20260721_01
Revises:
Create Date: 2026-07-21
"""

from __future__ import annotations

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


# Alembic reads these identifiers to place the file in its revision graph. A
# ``None`` down revision marks this file as the migration history root.
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
    """Return whether columns already have the requested index or constraint.

    Some database backends report a unique constraint separately from indexes,
    so unique lookups check both inspector collections before deciding to create
    anything. Comparing column tuples keeps composite-index order significant.
    """
    expected_columns = tuple(columns)
    for index in inspector.get_indexes(table_name):
        if tuple(index.get("column_names") or ()) != expected_columns:
            continue
        if unique is None or bool(index.get("unique")) is unique:
            return True

    if unique:
        # PostgreSQL may expose uniqueness as a constraint rather than through
        # ``get_indexes`` depending on how the legacy schema was created.
        for constraint in inspector.get_unique_constraints(table_name):
            if tuple(constraint.get("column_names") or ()) == expected_columns:
                return True
    return False


def _normalize_existing_emails(bind: sa.Connection) -> None:
    """Normalize legacy emails before enforcing case-consistent uniqueness.

    The operation first detects collisions such as ``User@example.com`` and
    `` user@example.com ``. It aborts before updating any row when normalization
    would merge two accounts, leaving manual conflict resolution to a developer.
    """
    # Reflect only the existing table so this adoption path works independently
    # of the current SQLModel class definitions.
    metadata = sa.MetaData()
    user_table = sa.Table("user", metadata, autoload_with=bind)
    normalized_mail = sa.func.lower(sa.func.trim(user_table.c.mail))

    # Search for one collision efficiently; the exact duplicate values are not
    # included in the exception to avoid leaking user email addresses in logs.
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

    # Lowercase and trim every legacy email in one set-based SQL update.
    bind.execute(user_table.update().values(mail=normalized_mail))


def upgrade() -> None:
    """Create a fresh portfolio schema or safely adopt the legacy schema."""
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    tables = set(inspector.get_table_names())

    if "user" not in tables:
        # A fresh database receives the complete user table and its unique email
        # index directly from this revision.
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
        # A legacy table may contain mixed-case or padded emails and may lack the
        # uniqueness now declared by schemas/User.py.
        _normalize_existing_emails(bind)
        # Refresh inspection after data/schema operations; Inspector caches
        # backend metadata and must not be assumed to reflect later changes.
        inspector = sa.inspect(bind)
        if not _has_index(inspector, "user", ["mail"], unique=True):
            op.create_index("ix_user_mail", "user", ["mail"], unique=True)

    # Re-read table names because the user table may have just been created.
    inspector = sa.inspect(bind)
    tables = set(inspector.get_table_names())

    if "experience" not in tables:
        # New installations receive ownership, date-ordering, and lookup
        # performance guarantees as part of table creation.
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
        # Adopt a pre-Alembic experience table by adding only missing structures.
        inspector = sa.inspect(bind)
        if not _has_index(inspector, "experience", ["user_id"]):
            op.create_index(
                "ix_experience_user_id", "experience", ["user_id"], unique=False
            )
        check_names = {
            check.get("name") for check in inspector.get_check_constraints("experience")
        }
        # This first revision avoids rebuilding a populated legacy SQLite table.
        # PostgreSQL can add the named check constraint in place.
        if (
            bind.dialect.name != "sqlite"
            and "ck_experience_date_order" not in check_names
        ):
            op.create_check_constraint(
                "ck_experience_date_order",
                "experience",
                "date_end >= date_start",
            )

    # Refresh once more because prior branches may have changed the schema.
    inspector = sa.inspect(bind)
    tables = set(inspector.get_table_names())

    if "education" not in tables:
        # Create the complete education table when no legacy equivalent exists.
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
        # Preserve legacy education rows while adding missing indexes and the
        # database-level date-order check supported by PostgreSQL.
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
    """Remove the initial schema and all portfolio data it contains.

    Downgrading this root revision is intentionally destructive. Indexes are
    removed before their owning tables to make the operation explicit across
    supported database backends.
    """
    op.drop_index("ix_education_user_id", table_name="education")
    op.drop_table("education")
    op.drop_index("ix_experience_user_id", table_name="experience")
    op.drop_table("experience")
    op.drop_index("ix_user_mail", table_name="user")
    op.drop_table("user")
