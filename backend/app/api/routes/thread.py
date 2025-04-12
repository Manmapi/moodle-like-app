from typing import Optional, List, Dict
from fastapi import APIRouter, HTTPException
from app.api.deps import CurrentUser, SessionDep
from app.models.post import Post, PostCreate, PostResponse, PostReaction
from sqlmodel import SQLModel, Field, select, update        
from app.models.thread import ThreadCreate, Thread
from app.data_access.thread import get_parent_thread
from app.data_access import neo4j
from collections import defaultdict 
from datetime import datetime
from app.api.deps import Neo4jSessionDep
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
    children: List["ThreadWithChildren"] = Field(default_factory=list)

class ThreadResponse(SQLModel):
    id: int
    title: str
    level: int
    user_id: int
    parent_id: int | None   
    children_count: int
    updated_at: datetime

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
    q = update(Thread).where(Thread.id == thread_id).values(children_count=Thread.children_count + 1, updated_at=datetime.now())
    session.exec(q)
    session.commit()
    session.refresh(db_thread)
    return db_thread.children_count

@router.post("/", response_model=ThreadWithPosts)
def create_thread(session: SessionDep, thread: ThreadCreate, current_user: CurrentUser):
    
    parent_thread = get_parent_thread(session, thread.parent_id) if thread.parent_id is not None else None  

    error_message = can_create_thread(current_user, thread, parent_thread)
    if error_message is not None:
        raise HTTPException(status_code=403, detail=error_message)
    
    db_thread = Thread(**thread.model_dump(), user_id=current_user.id, children_count=1)
    session.add(db_thread)  
    session.commit()

    update_q = update(Thread).where(Thread.id == thread.parent_id).values(children_count=Thread.children_count + 1)
    session.exec(update_q)
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

# TODO: Cache this response later once we set up Redis.
@router.get("/homepage", response_model=ThreadWithChildren)
def get_homepage(session: SessionDep):
    parent = session.exec(select(Thread).where(Thread.level == 0)).first()
    if parent is None:
        raise HTTPException(status_code=404, detail="Thread not found")
    frist_level_threads = session.exec(select(Thread).where(Thread.parent_id == parent.id)).all()
    second_level_threads = []
    first_level_thread_ids = [thread.id for thread in frist_level_threads]
    second_level_threads = session.exec(select(Thread).where(Thread.parent_id.in_(first_level_thread_ids))).all()

    second_level_thread_mapping = {}

    for second_level_thread in second_level_threads:
        if second_level_thread.parent_id not in second_level_thread_mapping:
            second_level_thread_mapping[second_level_thread.parent_id] = []
        second_level_thread_mapping[second_level_thread.parent_id].append(second_level_thread)

    first_level_thread_respone = [ThreadWithChildren(
        id=thread.id,
        title=thread.title,
        level=thread.level,
        user_id=thread.user_id,
        parent_id=thread.parent_id,
        children=second_level_thread_mapping[thread.id]
    ) for thread in frist_level_threads]

    return ThreadWithChildren(
        id=parent.id,
        title=parent.title,
        level=parent.level,
        user_id=parent.user_id,
        parent_id=parent.parent_id,
        children_count=parent.children_count,
        children=first_level_thread_respone
    )


@router.get("/similar_threads", response_model=List[ThreadResponse])
def get_similar_threads(session: SessionDep, thread_id: int, neo4j_session: Neo4jSessionDep):
    db_thread = session.exec(select(Thread).where(Thread.id == thread_id)).first()
    if db_thread is None:
        raise HTTPException(status_code=404, detail="Thread not found")
    # List[thread_id, related_tags: int]
    similar_threads = neo4j.get_similar_threads(neo4j_session, db_thread.id, limit=5)
    scores_mapping = defaultdict(list)
    scores = [] 
    for similar_thread in similar_threads:
        thread_id = similar_thread["threadId"]
        related_tags = similar_thread["sharedTags"]
        scores_mapping[related_tags].append(thread_id)
        scores.append(related_tags)
    scores.sort(reverse=True)   
    # We query based on related_tags descending order until we get 5. Also query based on updated_at descending order.
    result = []
    for score in scores:
        thread_ids = scores_mapping[score]
        query = select(Thread).where(Thread.id.in_(thread_ids)).order_by(Thread.updated_at.desc())
        similar_threads = session.exec(query).all() 
        result.extend(similar_threads)
        if len(result) >= 5:
            break
    return result[:5]

class PaginatedThread(SQLModel):
    threads: List[ThreadResponse]
    total: int


@router.get("/{thread_id}/get_third_level_thread", response_model=PaginatedThread)
def get_third_level_thread(session: SessionDep, parent_thread_id: int, limit: int = 10, offset: int = 0):
    parent_thread = session.exec(select(Thread).where(Thread.id == parent_thread_id)).first()   
    if parent_thread is None:
        raise HTTPException(status_code=404, detail="Parent thread not found")
    if parent_thread.level != 2:
        raise HTTPException(status_code=403, detail="Parent thread is not a second level thread")
    threads = session.exec(select(Thread).where(Thread.parent_id == parent_thread.id).order_by(Thread.updated_at.desc()).offset(offset).limit(limit)).all()
    return PaginatedThread(threads=threads, total=len(threads))

@router.get("/{thread_id}", response_model=ThreadResponse)
def get_thread(session: SessionDep, thread_id: int):
    db_thread = session.exec(select(Thread).where(Thread.id == thread_id)).first()
    return db_thread

@router.get("/{thread_id}/posts", response_model=List[PostResponse])
def get_posts(session: SessionDep, thread_id: int, limit: int = 10, offset: int = 0):
    thread = session.exec(select(Thread).where(Thread.id == thread_id)).first()
    if thread is None:
        raise HTTPException(status_code=404, detail="Thread not found") 
    if thread.level != 3:
        raise HTTPException(status_code=400, detail="Thread is not a third level thread")
    db_posts = session.exec(select(Post).where(Post.thread_id == thread_id).order_by(Post.id.asc()).offset(offset).limit(limit)).all()
    return db_posts 

@router.get("/posts/reaction/{post_id}", response_model=Dict[int, PostReaction])
def get_post_reactions(session: SessionDep, post_ids: List[int]):
    db_posts = session.exec(select(PostReaction).where(PostReaction.post_id.in_(post_ids))).all()
    return {post_id: db_posts for post_id in post_ids}


