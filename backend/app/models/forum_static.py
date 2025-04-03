from sqlmodel import Field, SQLModel

# We will use cronjob to udpate this table per 5' mins
class ForumStatic(SQLModel, table=True):
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    thread_count: int = Field(default=0)
    post_count: int = Field(default=0)
    user_count: int = Field(default=0)
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)

    lastest_user: User | None = Field(default=None)
