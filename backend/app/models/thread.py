import uuid
from datetime import datetime

from pydantic import EmailStr
from sqlmodel import Field, Relationship, SQLModel


class Thread(SQLModel, table=True):
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    title: str
    tags: list[str] = Field(default=[])
    created_by: uuid.UUID = Field(foreign_key="user.id")
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)

    # Level for thread from 0 to 2 
    level: int = Field(default=0)
    parent_id: uuid.UUID | None = Field(foreign_key="thread.id")
    parent: "Thread" | None = Relationship(back_populates="children")
    children: list["Thread"] = Relationship(back_populates="parent")

    # Only admin can pin a thread.
    is_pinned: bool = Field(default=False)

class ThreadCreate(SQLModel):
    title: str
    tags: list[str] = Field(default=[])

class ThreadUpdate(SQLModel):
    title: str | None = None
    tags: list[str] | None = None

class ThreadRead(SQLModel):
    id: uuid.UUID
    title: str
    tags: list[str]
    created_by: uuid.UUID
    created_at: datetime
    updated_at: datetime

class ThreadReadWithUser(ThreadRead):
    created_by: User

