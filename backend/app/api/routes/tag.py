from fastapi import APIRouter, HTTPException
from sqlmodel import Session, select, update
from app.models.thread import Tag, ThreadTag
from app.models.thread import Thread
from app.api.deps import CurrentUser, SessionDep, Neo4jSessionDep
from typing import List
from sqlmodel import SQLModel
from app.data_access import neo4j
from sqlalchemy.dialects.postgresql import insert

router = APIRouter(prefix="/tag", tags=["tag"])

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
def add_tags_to_thread(tag_ids: list[int], thread_id: int, session: SessionDep, neo4j_session: Neo4jSessionDep, current_user: CurrentUser):
    if current_user.level != 0:
        raise HTTPException(status_code=403, detail="Only admin can add thread to tag")
    
    thread = session.exec(select(Thread).where(Thread.id == thread_id)).first()
    
    if thread is None:
        raise HTTPException(status_code=404, detail="Thread not found")
    # Check if all tags exist
    tags = session.exec(select(Tag).where(Tag.id.in_(tag_ids))).all()
    if len(tags) != len(tag_ids):
        raise HTTPException(status_code=404, detail="One or more tags not found")   
    
    
    insert_data = []
    for tag_id in tag_ids:
        data = {
            "tag_id": tag_id,
            "thread_id": thread_id
        }
        
        insert_data.append(data)
    q = insert(ThreadTag).values(insert_data).on_conflict_do_nothing(index_elements=["tag_id", "thread_id"])
    session.exec(q)
    # Add tag to neo4j
    session.commit()
    neo4j.add_tags_to_thread(thread_id, tag_ids, neo4j_session=neo4j_session)

    return {"message": "Tags added to thread"}   
