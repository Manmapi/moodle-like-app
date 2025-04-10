from sqlmodel import Session, select

from app.models.thread import Thread, ThreadCreate
from app.api.deps import CurrentUser

def create_thread(db: Session, thread: ThreadCreate, user: CurrentUser) -> Thread:
    db_thread = Thread(**thread.model_dump(), user_id=user.id)
    db.add(db_thread)   
    db.commit()
    db.refresh(db_thread)
    return db_thread

def get_thread(db: Session, thread_id: int) -> Thread | None:
    return db.exec(select(Thread).where(Thread.id == thread_id)).first()

def get_thread_by_user(db: Session, user_id: int) -> list[Thread]:
    return db.exec(select(Thread).where(Thread.user_id == user_id)).all()

def get_thread_by_parent(db: Session, parent_id: int) -> list[Thread]:
    return db.exec(select(Thread).where(Thread.parent_id == parent_id)).all()

def get_thread_by_level(db: Session, level: int) -> list[Thread]:
    return db.exec(select(Thread).where(Thread.level == level)).all()


def get_parent_thread(db: Session, thread_id: int) -> Thread | None:
    return db.exec(select(Thread).where(Thread.id == thread_id)).first()  
    