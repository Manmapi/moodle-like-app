from app.models.post import Post, PostCreate
from app.api.deps import CurrentUser
from sqlmodel import Session, select

def create_post(db: Session, post: PostCreate, user: CurrentUser) -> Post:
    db_post = Post(**post.model_dump(), user_id=user.id)
    db.add(db_post)
    db.commit()
    db.refresh(db_post)
    return db_post

def get_post(db: Session, post_id: int) -> Post | None:
    return db.exec(select(Post).where(Post.id == post_id)).scalars.first()

def get_posts_by_thread(db: Session, thread_id: int) -> list[Post]:
    return db.exec(select(Post).where(Post.thread_id == thread_id)).scalars().all()

def get_posts_by_user(db: Session, user_id: int) -> list[Post]:
    return db.exec(select(Post).where(Post.user_id == user_id)).scalars().all()
    