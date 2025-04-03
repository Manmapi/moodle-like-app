from sqlmodel import Field, SQLModel

class Post(SQLModel, table=True):
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    title: str
    content: str
    image_urls: list[str] = Field(default=[])
    created_at: datetime
    thread_id: uuid.UUID = Field(foreign_key="thread.id")
    thread: Thread = Relationship(back_populates="posts")

    quote_id: uuid.UUID | None = Field(foreign_key="post.id")
    quote: Post | None = Relationship(back_populates="quotes")

    created_by: uuid.UUID = Field(foreign_key="user.id")

    reaction_count: int = Field(default=0)

class PostCreate(SQLModel):
    title: str
    content: str
    image_urls: list[str] = Field(default=[])
    quote_id: uuid.UUID | None = Field(foreign_key="post.id")

class PostRead(SQLModel):
    id: uuid.UUID
    title: str
    content: str
    image_urls: list[str]
    created_at: datetime
    created_by: uuid.UUID   

class ReactionType(Enum):
    LIKE = "like"
    DISLIKE = "dislike"

class Reaction(SQLModel, table=True):
    post_id: uuid.UUID = Field(foreign_key="post.id", primary_key=True)
    user_id: uuid.UUID = Field(foreign_key="user.id", primary_key=True)
    type: ReactionType

    user: User = Relationship(back_populates="reactions")
    post: Post = Relationship(back_populates="reactions")

