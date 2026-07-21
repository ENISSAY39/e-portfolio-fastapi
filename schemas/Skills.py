"""Define skills displayed on a user's portfolio."""

from typing import Optional

from sqlalchemy import CheckConstraint
from sqlmodel import Field, SQLModel


class Skill(SQLModel, table=True):
    """Store one named skill and its self-assessed proficiency level."""

    __table_args__ = (
        CheckConstraint(
            "level >= 1 AND level <= 5",
            name="ck_skill_level_range",
        ),
    )

    id: Optional[int] = Field(default=None, primary_key=True)
    name: str
    level: int
    user_id: int = Field(foreign_key="user.id", index=True)
