from typing import List

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlmodel import Session, select

from app.api.deps import SessionDep
from app.models.post import Post, PostResponse

router = APIRouter(prefix="/post", tags=["post"])

@router.get("/", response_model=List[PostResponse])
def get_posts_by_ids(
    session: SessionDep,
    post_ids: List[int] = Query(..., description="List of post IDs to fetch")
):
    """
    Retrieve multiple posts by their IDs.
    """
    if not post_ids:
        return [] # Return empty list if no IDs are provided
        
    statement = select(Post).where(Post.id.in_(post_ids))
    db_posts = session.exec(statement).all()
    
    if not db_posts:
        return []

    return db_posts 
