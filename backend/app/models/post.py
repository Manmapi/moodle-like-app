from sqlmodel import Field, SQLModel
from datetime import datetime

class Post(SQLModel, table=True):
    id: int = Field(default=None, primary_key=True)
    thread_id: int = Field(foreign_key="thread.id")
    user_id: int = Field(foreign_key="user.id")
    content: str

    # Denormalized field for better performance
    quote_ids: list[int] = Field(default_factory=list)

    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)

class PostReaction(SQLModel, table=True):
    id: int = Field(default=None, primary_key=True)
    post_id: int = Field(foreign_key="post.id")
    user_id: int = Field(foreign_key="user.id")
    reaction_type: int

    created_at: datetime = Field(default_factory=datetime.now)

class PostCreate(SQLModel):
    thread_id: int
    content: str
    user_id: int
    quote_ids: list[int] = Field(default_factory=list)
