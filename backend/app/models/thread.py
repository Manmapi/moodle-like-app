from sqlmodel import Field, SQLModel
from datetime import datetime

class Thread(SQLModel, table=True):
    id: int = Field(default=None, primary_key=True)
    title: str
    level: int
    user_id: int = Field(foreign_key="user.id")
    parent_id: int | None = Field(default=None, foreign_key="thread.id")

    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)

class ThreadView(SQLModel, table=True):
    id: int = Field(default=None, primary_key=True)
    thread_id: int = Field(foreign_key="thread.id")
    user_id: int = Field(foreign_key="user.id")
    created_at: datetime = Field(default_factory=datetime.now)

class ThreadCreate(SQLModel):
    title: str
    level: int
    user_id: int
    parent_id: int | None = None
    