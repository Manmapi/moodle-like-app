from typing import Optional, List
from uuid import UUID
from sqlmodel import select
from datetime import datetime

from app.core.db_facade import db_facade
from app.models.thread import Thread, ThreadCreate, ThreadUpdate

class PostDataAccess:
    """Data access layer for posts/threads"""
    
    async def create_thread(
        self,
        thread_in: ThreadCreate,
        created_by: UUID,
        parent_id: Optional[UUID] = None
    ) -> Thread:
        """Create a new thread"""
        thread = await db_facade.create_thread_with_metrics(
            title=thread_in.title,
            tags=thread_in.tags,
            created_by=str(created_by)
        )
        
        if parent_id:
            # Create parent-child relationship in Neo4j
            async with db_facade.get_neo4j_session() as neo4j:
                await neo4j.run(
                    """
                    MATCH (parent:Thread {id: $parent_id})
                    MATCH (child:Thread {id: $child_id})
                    CREATE (parent)-[:HAS_CHILD]->(child)
                    """,
                    parent_id=str(parent_id),
                    child_id=str(thread.id)
                )
        
        return thread

    async def get_thread(self, thread_id: UUID) -> Optional[Thread]:
        """Get a thread by ID"""
        result = await db_facade.get_thread_with_metrics(str(thread_id))
        return result["thread"] if result else None

    async def get_threads_by_user(self, user_id: UUID) -> List[Thread]:
        """Get all threads created by a user"""
        async with db_facade.get_postgres_session() as session:
            query = select(Thread).where(Thread.created_by == user_id)
            result = await session.exec(query)
            return result.all()

    async def update_thread(
        self,
        thread_id: UUID,
        thread_in: ThreadUpdate
    ) -> Optional[Thread]:
        """Update a thread"""
        async with db_facade.get_postgres_session() as session:
            thread = await session.get(Thread, thread_id)
            if not thread:
                return None

            # Update fields if provided
            if thread_in.title is not None:
                thread.title = thread_in.title
            if thread_in.tags is not None:
                thread.tags = thread_in.tags
            
            thread.updated_at = datetime.utcnow()
            
            session.add(thread)
            await session.commit()
            await session.refresh(thread)
            
            # Update Neo4j if title changed
            if thread_in.title is not None:
                async with db_facade.get_neo4j_session() as neo4j:
                    await neo4j.run(
                        """
                        MATCH (t:Thread {id: $id})
                        SET t.title = $title
                        """,
                        id=str(thread_id),
                        title=thread_in.title
                    )
            
            return thread

    async def delete_thread(self, thread_id: UUID) -> bool:
        """Delete a thread"""
        async with db_facade.get_postgres_session() as session:
            thread = await session.get(Thread, thread_id)
            if not thread:
                return False
            
            await session.delete(thread)
            await session.commit()
            
            # Delete from Neo4j
            async with db_facade.get_neo4j_session() as neo4j:
                await neo4j.run(
                    """
                    MATCH (t:Thread {id: $id})
                    DETACH DELETE t
                    """,
                    id=str(thread_id)
                )
            
            return True

# Create a singleton instance
post_dao = PostDataAccess() 