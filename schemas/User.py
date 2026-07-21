from sqlmodel import SQLModel, Field
from typing import Optional
from datetime import date


class User(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str
    first_name: str
    birth_date: date
    mail: str = Field(index=True, unique=True)
    phone: str
    hashed_password: str
