from typing import Optional
from fastapi import APIRouter, HTTPException
from app.api.deps import CurrentUser, SessionDep

from app.models.thread import ThreadCreate, Thread
from app.data_access.thread import get_parent_thread

router = APIRouter(prefix="/thread", tags=["thread"])


def can_create_thread(current_user: CurrentUser, thread: ThreadCreate, parent_thread: Thread | None) -> Optional[str]:
    if current_user.level > 0 and thread.parent_id is None:
        return "Only admin can create thread"
    if parent_thread is not None and parent_thread.level > 1:
        return "User only allow to create thread with parent thread level is 1."
    if parent_thread is None and thread.parent_id is not None:
        return "Parent thread not found"    
    if thread.level >= 1 and parent_thread is None:
        return "Not root thread must have parent thread."   
    return None

@router.post("/thread")
def create_thread(session: SessionDep, thread: ThreadCreate, current_user: CurrentUser):
    
    parent_thread = get_parent_thread(session, thread.parent_id) if thread.parent_id is not None else None  

    error_message = can_create_thread(current_user, thread, parent_thread)
    if error_message is not None:
        raise HTTPException(status_code=403, detail=error_message)

    db_thread = Thread(**thread.model_dump(), user_id=current_user.id)
    session.add(db_thread)  
    session.commit()
    session.refresh(db_thread)
    return db_thread

@router.get("/thread/{thread_id}")
def get_thread(session: SessionDep, thread_id: int):
    db_thread = session.exec(select(Thread).where(Thread.id == thread_id)).first()
    return db_thread

# Get root thread with level = 0, has only one root thread  
@router.get("/thread/root")
def get_root_thread(session: SessionDep):
    db_thread = session.exec(select(Thread).where(Thread.level == 0)).first()
    return db_thread

# Get child threads of a thread
@router.get("/thread/{thread_id}/children")
def get_children_threads(session: SessionDep, thread_id: int):
    db_threads = session.exec(select(Thread).where(Thread.parent_id == thread_id)).all()
    return db_threads
