from sqlmodel import Field, SQLModel
from datetime import datetime
from sqlalchemy import BigInteger, Column

class Thread(SQLModel, table=True):
    id: int = Field(default=None, sa_column=Column(BigInteger, primary_key=True, autoincrement=True))
    title: str 
    level: int = Field(index=True)

    user_id: int = Field(foreign_key="user.id", sa_type=BigInteger)
    parent_id: int | None = Field(default=None, foreign_key="thread.id", sa_type=BigInteger)

    children_count: int = Field(default=0)
    
    updated_at: datetime = Field(default_factory=datetime.now, index=True)
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)

class ThreadView(SQLModel, table=True):
    id: int = Field(default=None, sa_column=Column(BigInteger, primary_key=True, autoincrement=True))
    thread_id: int = Field(foreign_key="thread.id", sa_type=BigInteger)
    user_id: int = Field(foreign_key="user.id", sa_type=BigInteger)
    created_at: datetime = Field(default_factory=datetime.now)

class ThreadCreate(SQLModel):
    title: str
    parent_id: int | None = None
    content: str | None = None

