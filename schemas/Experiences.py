"""Define professional-experience records owned by portfolio users."""

from datetime import datetime
from sqlalchemy import CheckConstraint
from sqlmodel import SQLModel, Field
from typing import Optional


class Experience(SQLModel, table=True):
    """Store one dated professional experience belonging to a user."""

    # Enforce chronological order in the database as a final safeguard even
    # when a write bypasses the HTML form validation layer.
    __table_args__ = (
        CheckConstraint("date_end >= date_start", name="ck_experience_date_order"),
    )

    # Primary keys are database-generated; new Python instances therefore begin
    # with no identifier.
    id: Optional[int] = Field(default=None, primary_key=True)
    title: str
    date_start: datetime
    date_end: datetime
    description: str
    company: str
    # The foreign key models ownership. Its index speeds up profile queries and
    # ownership checks that filter experiences by user.
    user_id: int = Field(foreign_key="user.id", index=True)
