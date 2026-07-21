"""Define portfolio projects owned by application users."""

from typing import Optional

from sqlmodel import Field, SQLModel


class Project(SQLModel, table=True):
    """Store one project and its optional technologies and destinations."""

    id: Optional[int] = Field(default=None, primary_key=True)
    title: str
    description: str
    technologies: Optional[str] = Field(default=None)
    project_url: Optional[str] = Field(default=None)
    repository_url: Optional[str] = Field(default=None)
    user_id: int = Field(foreign_key="user.id", index=True)
