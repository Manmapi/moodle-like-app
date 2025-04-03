from sqlmodel import Field, SQLModel


class WatchedThread(SQLModel, table=True):
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    user_id: uuid.UUID = Field(foreign_key="user.id", index=True)
    thread_id: uuid.UUID = Field(foreign_key="thread.id", index=True)
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)

    last_viewed_at: datetime = Field(default_factory=datetime.now)

    user: User = Relationship(back_populates="watched_threads")
    thread: Thread = Relationship(back_populates="watched_threads")

