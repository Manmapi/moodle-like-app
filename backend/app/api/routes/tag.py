from fastapi import APIRouter, HTTPException
from sqlmodel import Session, select, insert, update
from app.models.thread import Tag, ThreadTag
from app.api.deps import CurrentUser, SessionDep
from typing import List
from sqlmodel import SQLModel
router = APIRouter(prefix="/tag", tags=["tag"]  )

class CreateTag(SQLModel):
    name: str
    description: str | None = None

@router.post("/", response_model=Tag)
def create_tag(tag: CreateTag, session: SessionDep, current_user: CurrentUser):
    if current_user.level != 0:
        raise HTTPException(status_code=403, detail="Only admin can create tag")
    db_tag = Tag(**tag.model_dump())
    session.add(db_tag)
    session.commit()
    session.refresh(db_tag)
    return db_tag

@router.get("/", response_model=List[Tag])
def get_tags(session: SessionDep):
    tags = session.exec(select(Tag)).all()
    return tags

@router.post("/{tag_id}/thread", response_model=ThreadTag)
def add_thread_to_tag(tag_id: int, thread_id: int, session: SessionDep, current_user: CurrentUser):
    if current_user.level != 0:
        raise HTTPException(status_code=403, detail="Only admin can add thread to tag")
    thread_tag = ThreadTag(tag_id=tag_id, thread_id=thread_id)
    session.add(thread_tag)
    session.commit()
    return thread_tag   

