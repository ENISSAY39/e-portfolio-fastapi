from datetime import datetime
from sqlmodel import SQLModel, Field
from typing import Optional


class Experience(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    title: str
    date_start: datetime
    date_end: datetime
    description: str
    company: str
    user_id: int = Field(foreign_key="user.id")
