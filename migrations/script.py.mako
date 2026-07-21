"""${message}

Revision ID: ${up_revision}
Revises: ${down_revision | comma,n}
Create Date: ${create_date}

This file was generated from Alembic's project template. Review every generated
operation before applying it, especially destructive column or table changes.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
${imports if imports else ""}


# Alembic uses these identifiers to order this revision in the migration graph.
revision: str = ${repr(up_revision)}
down_revision: Union[str, Sequence[str], None] = ${repr(down_revision)}
branch_labels: Union[str, Sequence[str], None] = ${repr(branch_labels)}
depends_on: Union[str, Sequence[str], None] = ${repr(depends_on)}


def upgrade() -> None:
    """Apply this revision's forward schema transformations."""
    ${upgrades if upgrades else "pass"}


def downgrade() -> None:
    """Reverse this revision when a rollback is explicitly requested."""
    ${downgrades if downgrades else "pass"}
