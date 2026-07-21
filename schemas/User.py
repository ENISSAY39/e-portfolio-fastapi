"""Define the persisted SQLModel representation of an application user."""

from sqlmodel import SQLModel, Field
from typing import Optional
from datetime import date


class User(SQLModel, table=True):
    """Store identity, contact information, and authentication credentials.

    The class is both a Python validation model and the ``user`` SQL table
    because ``table=True`` is set. Passwords must be hashed before construction;
    this model never stores a plaintext password.
    """

    # ``None`` lets the database generate the primary key on insertion.
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str
    first_name: str
    birth_date: date
    # The unique index enforces one normalized email per account at database
    # level and accelerates login/authentication lookups.
    mail: str = Field(index=True, unique=True)
    phone: str
    hashed_password: str
    # The biography is optional so existing accounts and freshly registered
    # users remain valid until they choose to complete their portfolio.
    bio: Optional[str] = Field(default=None)
