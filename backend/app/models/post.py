from sqlmodel import Field, SQLModel
from datetime import datetime
from sqlalchemy.dialects.postgresql import ARRAY
from sqlalchemy import Integer, BigInteger, Column

class Post(SQLModel, table=True):
    id: int = Field(default=None, sa_column=Column(BigInteger, primary_key=True, autoincrement=True))
    thread_id: int = Field(foreign_key="thread.id", sa_type=BigInteger)
    user_id: int = Field(foreign_key="user.id", sa_type=BigInteger)
    content: str

    # Denormalized field for better performance
    quote_ids: list[int] = Field(sa_type=ARRAY(Integer), default_factory=list)

    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)

class PostReaction(SQLModel, table=True):
    id: int = Field(default=None, sa_column=Column(BigInteger, primary_key=True, autoincrement=True))
    post_id: int = Field(foreign_key="post.id", index=True, sa_type=BigInteger)
    user_id: int = Field(foreign_key="user.id", sa_type=BigInteger)
    reaction_type: int

    created_at: datetime = Field(default_factory=datetime.now)

class PostCreate(SQLModel):
    thread_id: int
    content: str
    user_id: int
    quote_ids: list[int] = Field(default_factory=list)

class PostResponse(SQLModel):
    id: int
    thread_id: int
    user_id: int
    content: str
    quote_ids: list[int]
    created_at: datetime
    updated_at: datetime
