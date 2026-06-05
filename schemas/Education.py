from datetime import datetime
from sqlmodel import SQLModel, Field
from typing import Optional


class Education(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    school_name: str
    date_start: datetime
    date_end: datetime
    description: str
    major: str

    user_id: int = Field(foreign_key="user.id")
