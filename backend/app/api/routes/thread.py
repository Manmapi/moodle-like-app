from typing import Optional, List, Dict
from fastapi import APIRouter, HTTPException
from app.api.deps import CurrentUser, SessionDep
from app.models.post import Post, PostCreate, PostResponse, PostReaction
from sqlmodel import SQLModel, Field, select, update        
from app.models.thread import ThreadCreate, Thread, ThreadView
from app.models.category import Category
from app.data_access import neo4j
from collections import defaultdict 
from datetime import datetime
from app.api.deps import Neo4jSessionDep
from app.core.redis import redis_conn
from app.tasks.thread import record_thread_view
from app.worker import example_task

from sqlalchemy import text
router = APIRouter(prefix="/thread", tags=["thread"])

# Constants for caching
HOMEPAGE_CACHE_KEY = "homepage_data"
HOMEPAGE_CACHE_TTL = 30 * 60  # 30 minutes in seconds

class ThreadWithPosts(SQLModel):
    id: int
    title: str
    user_id: int
    category_id: int | None
    posts: List["PostResponse"] = Field(default_factory=list)

class CategoryWithChildren(SQLModel):
    id: int
    title: str
    level: int
    user_id: int
    parent_id: int | None
    children_count: int
    children: List["CategoryWithChildren"] = Field(default_factory=list)

class ThreadResponse(SQLModel):
    id: int
    title: str
    user_id: int
    category_id: int | None   
    children_count: int
    updated_at: datetime


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
    category = session.exec(select(Category).where(Category.id == thread.category_id)).first()
    if category is None:
        raise HTTPException(status_code=404, detail="Category not found")   
    if category.level != 2:
        raise HTTPException(status_code=400, detail="Only create thread in second level category")
    
    db_thread = Thread(**thread.model_dump(), user_id=current_user.id, children_count=1)
    session.add(db_thread)  
    session.commit()

    update_q = update(Thread).where(Thread.id == thread.category_id).values(children_count=Thread.children_count + 1)
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
        user_id=db_thread.user_id,
        category_id=db_thread.category_id,
        posts=children,
    )

# TODO: Cache this response later once we set up Redis.
@router.get("/homepage", response_model=CategoryWithChildren)
async def get_homepage(session: SessionDep):
    # Try to get from cache first
    cached_homepage = await redis_conn.get_cached_object(HOMEPAGE_CACHE_KEY)
    
    if cached_homepage:
        # Convert the cached data to CategoryWithChildren models
        return CategoryWithChildren(**cached_homepage)
    
    # If not in cache, get from database
    parent = session.exec(select(Category).where(Category.level == 0)).first()
    if parent is None:
        raise HTTPException(status_code=404, detail="Category not found")
    frist_level_category = session.exec(select(Category).where(Category.parent_id == parent.id)).all()
    second_level_category = []
    first_level_category_ids = [category.id for category in frist_level_category]
    second_level_category = session.exec(select(Category).where(Category.parent_id.in_(first_level_category_ids))).all()

    second_level_category_mapping = {}

    for second_level_category in second_level_category:
        if second_level_category.parent_id not in second_level_category_mapping:
            second_level_category_mapping[second_level_category.parent_id] = []
        second_level_category_mapping[second_level_category.parent_id].append(second_level_category)

    first_level_category_respone = [CategoryWithChildren(
        id=category.id,
        title=category.title,
        level=category.level,
        user_id=category.user_id,
        parent_id=category.parent_id,
        children_count=category.children_count,
        children=second_level_category_mapping[category.id]
    ) for category in frist_level_category]

    result = CategoryWithChildren(
        id=parent.id,
        title=parent.title,
        level=parent.level,
        user_id=parent.user_id,
        parent_id=parent.parent_id,
        children_count=parent.children_count,
        children=first_level_category_respone
    )
    
    # Cache the result for 30 minutes
    await redis_conn.cache_object(HOMEPAGE_CACHE_KEY, result, HOMEPAGE_CACHE_TTL)
    
    return result


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


@router.get("/trending", response_model=List[ThreadResponse])
def get_trending_threads(session: SessionDep):
    """Get the top 10 trending threads based on view counts"""
    # First, get thread IDs from the materialized view in order of trending score
    trend_query = "SELECT id, trending_score FROM trending_threads ORDER BY trending_score DESC"
    thread_ids = [row[0] for row in session.exec(text(trend_query)).all()]
    trending_score_mapping = {row[0]: row[1] for row in session.exec(text(trend_query)).all()}
    print(trending_score_mapping)
    if not thread_ids:
        return []

    # Then fetch the full Thread objects using those IDs
    # The order_by clause preserves the order from the materialized view
    threads_query = select(Thread).where(Thread.id.in_(thread_ids))
    threads = session.exec(threads_query).all()

    # Sort the threads to match the order from the trending view
    # Create a mapping of id -> position in the trending list
    id_to_position = {id: idx for idx, id in enumerate(thread_ids)}

    # Sort threads based on their position in the trending list
    sorted_threads = sorted(threads, key=lambda t: id_to_position.get(t.id, 999))

    return sorted_threads

class PaginatedThread(SQLModel):
    threads: List[ThreadResponse]
    total: int


@router.get("/{thread_id}/get_third_level_thread", response_model=PaginatedThread)
def get_thread_by_category(session: SessionDep, category_id: int, limit: int = 10, offset: int = 0):
    category = session.exec(select(Category).where(Category.id == category_id)).first()   
    if category is None:
        raise HTTPException(status_code=404, detail="Parent thread not found")
    if category.level != 2:
        raise HTTPException(status_code=403, detail="Category is not a third level category")
    threads = session.exec(select(Thread).where(Thread.category_id == category.id).order_by(Thread.updated_at.desc()).offset(offset).limit(limit)).all()
    return PaginatedThread(threads=threads, total=len(threads))

@router.get("/{thread_id}", response_model=ThreadResponse)
def get_thread(session: SessionDep, thread_id: int):
    db_thread = session.exec(select(Thread).where(Thread.id == thread_id)).first()
    if db_thread is None:
        raise HTTPException(status_code=404, detail="Thread not found")
    return db_thread

@router.get("/{thread_id}/posts", response_model=List[PostResponse])
def get_posts(session: SessionDep, thread_id: int, limit: int = 10, offset: int = 0):
    thread = session.exec(select(Thread).where(Thread.id == thread_id)).first()
    if thread is None:
        raise HTTPException(status_code=404, detail="Thread not found") 
    db_posts = session.exec(select(Post).where(Post.thread_id == thread_id).order_by(Post.id.asc()).offset(offset).limit(limit)).all()
    return db_posts 

@router.get("/posts/reaction/{post_id}", response_model=Dict[int, PostReaction])
def get_post_reactions(session: SessionDep, post_ids: List[int]):
    db_posts = session.exec(select(PostReaction).where(PostReaction.post_id.in_(post_ids))).all()
    return {post_id: db_posts for post_id in post_ids}


@router.post("/{thread_id}/view")
def insert_thread_view(thread_id: int):
    # Send the view event to Celery task queue
    example_task.delay("thread_id")
    task = record_thread_view.delay(thread_id)
    return task.id


