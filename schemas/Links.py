"""Define external links attached to public portfolios."""

from typing import ClassVar, Optional

from sqlmodel import Field, SQLModel


class ExternalLink(SQLModel, table=True):
    """Store a labelled HTTP(S) link owned by one user."""

    __tablename__: ClassVar[str] = "external_link"

    id: Optional[int] = Field(default=None, primary_key=True)
    label: str
    url: str
    user_id: int = Field(foreign_key="user.id", index=True)
