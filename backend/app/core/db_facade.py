from typing import AsyncGenerator, Optional
from sqlmodel import Session
from neo4j import Session as Neo4jSession
from influxdb_client import InfluxDBClientAsync
from datetime import datetime

from app.core.db import engine
from app.core.neo4j import neo4j_conn
from app.core.influxdb import influxdb_conn

class DatabaseFacade:
    """Facade for all database operations"""
    
    async def get_postgres_session(self) -> AsyncGenerator[Session, None]:
        """Get PostgreSQL session"""
        with Session(engine) as session:
            yield session

    async def get_neo4j_session(self) -> AsyncGenerator[Neo4jSession, None]:
        """Get Neo4j session"""
        async with neo4j_conn.get_session() as session:
            yield session

    async def get_influxdb_client(self) -> AsyncGenerator[InfluxDBClientAsync, None]:
        """Get InfluxDB client"""
        async with influxdb_conn.get_client() as client:
            yield client

    async def write_metrics(self, bucket: str, measurement: str, fields: dict, tags: Optional[dict] = None):
        """Write metrics to InfluxDB"""
        point = {
            "measurement": measurement,
            "fields": fields,
            "time": datetime.utcnow()
        }
        if tags:
            point["tags"] = tags
        
        await influxdb_conn.write_data(bucket=bucket, record=point)

    async def create_thread_with_metrics(
        self,
        title: str,
        tags: list[str],
        created_by: str,
        bucket: str = "thread_metrics"
    ):
        """Create a thread and record metrics"""
        # Create thread in PostgreSQL
        async with self.get_postgres_session() as session:
            thread = Thread(
                title=title,
                tags=tags,
                created_by=created_by
            )
            session.add(thread)
            await session.commit()
            await session.refresh(thread)

        # Create thread node in Neo4j
        async with self.get_neo4j_session() as neo4j:
            await neo4j.run(
                "CREATE (t:Thread {id: $id, title: $title})",
                id=str(thread.id),
                title=title
            )

        # Record metrics in InfluxDB
        await self.write_metrics(
            bucket=bucket,
            measurement="thread_created",
            fields={"count": 1},
            tags={"thread_id": str(thread.id)}
        )

        return thread

    async def get_thread_with_metrics(
        self,
        thread_id: str,
        bucket: str = "thread_metrics"
    ):
        """Get thread with its metrics"""
        # Get thread from PostgreSQL
        async with self.get_postgres_session() as session:
            thread = await session.get(Thread, thread_id)
            if not thread:
                return None

        # Get thread relationships from Neo4j
        async with self.get_neo4j_session() as neo4j:
            result = await neo4j.run(
                "MATCH (t:Thread {id: $id})-[r]->(n) RETURN type(r) as rel_type, n",
                id=thread_id
            )
            relationships = [dict(record) for record in result]

        # Get thread metrics from InfluxDB
        query = f'''
            from(bucket: "{bucket}")
                |> range(start: -30d)
                |> filter(fn: (r) => r["_measurement"] == "thread_created")
                |> filter(fn: (r) => r["thread_id"] == "{thread_id}")
        '''
        metrics = await influxdb_conn.query_data(query=query)

        return {
            "thread": thread,
            "relationships": relationships,
            "metrics": metrics
        }

# Create a singleton instance
db_facade = DatabaseFacade() 