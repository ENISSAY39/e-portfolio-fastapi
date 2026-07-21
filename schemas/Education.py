"""Define education records displayed on a user's portfolio."""

from datetime import datetime
from sqlalchemy import CheckConstraint
from sqlmodel import SQLModel, Field
from typing import Optional


class Education(SQLModel, table=True):
    """Store one dated education entry belonging to a user."""

    # Mirror application validation at database level so an end date cannot be
    # persisted before its corresponding start date.
    __table_args__ = (
        CheckConstraint("date_end >= date_start", name="ck_education_date_order"),
    )

    # The database assigns the primary key when the row is inserted.
    id: Optional[int] = Field(default=None, primary_key=True)
    school_name: str
    date_start: datetime
    date_end: datetime
    description: str
    major: str

    # Education is owned through this foreign key; indexing it keeps per-user
    # listing and authorization queries efficient.
    user_id: int = Field(foreign_key="user.id", index=True)
