from typing import Optional, List, Dict
from fastapi import APIRouter, HTTPException
from app.api.deps import CurrentUser, SessionDep
from app.models.post import Post, PostCreate, PostResponse, PostReaction
from sqlmodel import SQLModel, Field, select, update        
from app.models.thread import ThreadCreate, Thread
from app.data_access.thread import get_parent_thread

router = APIRouter(prefix="/thread", tags=["thread"])



class ThreadWithPosts(SQLModel):
    id: int
    title: str
    level: int
    user_id: int
    parent_id: int | None
    posts: List["PostResponse"] = Field(default_factory=list)

class ThreadWithChildren(SQLModel):
    id: int
    title: str
    level: int
    user_id: int
    parent_id: int | None
    children: List["ThreadResponse"] = Field(default_factory=list)

class ThreadResponse(SQLModel):
    id: int
    title: str
    level: int
    user_id: int
    parent_id: int | None   
    post_count: int

def can_create_thread(current_user: CurrentUser, thread: ThreadCreate, parent_thread: Thread | None) -> Optional[str]:
    if current_user.level > 0 and thread.parent_id is None:
        return "Only admin can create thread"
    if parent_thread is not None and parent_thread.level != 2:
        return "User only allow to create thread with parent thread level is 2."
    if parent_thread is None and thread.parent_id is not None:
        return "Parent thread not found"  
    if thread.level >= 1 and parent_thread is None:
        return "Not root thread must have parent thread."   
    if thread.level == 3 and thread.content is None:
        return "Thread level 3 must have init content."
    return None


@router.post("/{thread_id}/post", response_model=int)
def create_post(session: SessionDep, thread_id: int, post: PostCreate, current_user: CurrentUser):
    if current_user.level > 1:
        raise HTTPException(status_code=403, detail="Junior level user can't create post")
    db_thread = session.exec(select(Thread).where(Thread.id == thread_id)).first()
    if db_thread is None:
        raise HTTPException(status_code=404, detail="Thread not found")
    db_post = Post(**post.model_dump(), thread_id=db_thread.id, user_id=current_user.id)
    session.add(db_post)
    # atomic increment post count
    q = update(Thread).where(Thread.id == thread_id).values(post_count=Thread.post_count + 1)
    session.exec(q)
    session.commit()
    session.refresh(db_thread)
    return db_thread.post_count

@router.post("/", response_model=ThreadWithPosts)
def create_thread(session: SessionDep, thread: ThreadCreate, current_user: CurrentUser):
    
    parent_thread = get_parent_thread(session, thread.parent_id) if thread.parent_id is not None else None  

    error_message = can_create_thread(current_user, thread, parent_thread)
    if error_message is not None:
        raise HTTPException(status_code=403, detail=error_message)
    
    db_thread = Thread(**thread.model_dump(), user_id=current_user.id, count_children=0, post_count=1)
    session.add(db_thread)  
    session.commit()
    if thread.content is not None:
        first_post = Post(thread_id=db_thread.id, user_id=current_user.id, content=thread.content)
        session.add(first_post)
        session.commit()
        session.refresh(db_thread)  
        session.refresh(first_post)
        children = [first_post]
    else:
        children = []
    return ThreadWithPosts(
        id=db_thread.id,
        title=db_thread.title,
        level=db_thread.level,
        user_id=db_thread.user_id,
        parent_id=db_thread.parent_id,
        posts=children,
    )

# Get root thread with level = 0, has only one root thread  
@router.get("/root", response_model=ThreadResponse)
def get_root_thread(session: SessionDep):
    db_thread = session.exec(select(Thread).where(Thread.level == 0)).first()
    return db_thread

@router.get("/{thread_id}", response_model=ThreadResponse)
def get_thread(session: SessionDep, thread_id: int):
    db_thread = session.exec(select(Thread).where(Thread.id == thread_id)).first()
    return db_thread

# Get child threads of a thread
@router.get("/{thread_id}/children", response_model=List[ThreadResponse])
def get_children_threads(session: SessionDep, thread_id: int):
    db_threads = session.exec(select(Thread).where(Thread.parent_id == thread_id).order_by(Thread.created_at.desc())).all()
    return db_threads

@router.get("/{thread_id}/children/all", response_model=ThreadWithChildren)
def get_thread_and_children(session: SessionDep, thread_id: int):
    parent = session.exec(select(Thread).where(Thread.id == thread_id)).first()
    if parent is None:
        raise HTTPException(status_code=404, detail="Thread not found")
    db_children = session.exec(select(Thread).where(Thread.parent_id == thread_id)).all()
    return ThreadWithChildren(
        id=parent.id,
        title=parent.title,
        level=parent.level,
        user_id=parent.user_id,
        parent_id=parent.parent_id,
        count_children=parent.count_children,
        children=db_children
    )


@router.get("/{thread_id}/posts", response_model=List[PostResponse])
def get_posts(session: SessionDep, thread_id: int, limit: int = 10, offset: int = 0):
    db_posts = session.exec(select(Post).where(Post.thread_id == thread_id).order_by(Post.id.asc()).offset(offset).limit(limit)).all()
    return db_posts 

@router.get("/posts/reaction/{post_id}", response_model=Dict[int, PostReaction])
def get_post_reactions(session: SessionDep, post_ids: List[int]):
    db_posts = session.exec(select(PostReaction).where(PostReaction.post_id.in_(post_ids))).all()
    return {post_id: db_posts for post_id in post_ids}


    