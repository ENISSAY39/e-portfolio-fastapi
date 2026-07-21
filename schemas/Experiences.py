from datetime import datetime
from sqlalchemy import CheckConstraint
from sqlmodel import SQLModel, Field
from typing import Optional


class Experience(SQLModel, table=True):
    __table_args__ = (
        CheckConstraint("date_end >= date_start", name="ck_experience_date_order"),
    )

    id: Optional[int] = Field(default=None, primary_key=True)
    title: str
    date_start: datetime
    date_end: datetime
    description: str
    company: str
    user_id: int = Field(foreign_key="user.id", index=True)
