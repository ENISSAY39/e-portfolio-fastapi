"""Add biographies, skills, projects, and external links.

Revision ID: 20260722_02
Revises: 20260721_01
Create Date: 2026-07-22
"""

from __future__ import annotations

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "20260722_02"
down_revision: str | None = "20260721_01"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Add the optional profile field and the three owned content tables."""
    # Nullable storage lets every pre-existing account migrate without an
    # artificial biography or a data backfill.
    with op.batch_alter_table("user") as batch_op:
        batch_op.add_column(sa.Column("bio", sa.String(), nullable=True))

    op.create_table(
        "skill",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("level", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.CheckConstraint(
            "level >= 1 AND level <= 5",
            name="ck_skill_level_range",
        ),
        sa.ForeignKeyConstraint(["user_id"], ["user.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_skill_user_id", "skill", ["user_id"], unique=False)

    op.create_table(
        "project",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("title", sa.String(), nullable=False),
        sa.Column("description", sa.String(), nullable=False),
        sa.Column("technologies", sa.String(), nullable=True),
        sa.Column("project_url", sa.String(), nullable=True),
        sa.Column("repository_url", sa.String(), nullable=True),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["user.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_project_user_id", "project", ["user_id"], unique=False)

    op.create_table(
        "external_link",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("label", sa.String(), nullable=False),
        sa.Column("url", sa.String(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["user.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_external_link_user_id",
        "external_link",
        ["user_id"],
        unique=False,
    )


def downgrade() -> None:
    """Remove Sprint 2 content while leaving the initial schema intact."""
    op.drop_index("ix_external_link_user_id", table_name="external_link")
    op.drop_table("external_link")
    op.drop_index("ix_project_user_id", table_name="project")
    op.drop_table("project")
    op.drop_index("ix_skill_user_id", table_name="skill")
    op.drop_table("skill")

    with op.batch_alter_table("user") as batch_op:
        batch_op.drop_column("bio")
