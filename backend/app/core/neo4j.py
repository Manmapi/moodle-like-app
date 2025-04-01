from neo4j import GraphDatabase
import asyncio
import os
from contextlib import asynccontextmanager

class Neo4jConnection:
    def __init__(self, uri=None, user=None, password=None, max_sessions=None):
        # Use environment variables with defaults
        self.uri = uri or os.getenv("NEO4J_URI", "bolt://neo4j:7687")
        self.user = user or os.getenv("NEO4J_USER", "neo4j")
        self.password = password or os.getenv("NEO4J_PASSWORD", "password")
        self.max_sessions = max_sessions or int(os.getenv("NEO4J_MAX_SESSIONS", "10"))

        # Initialize the Neo4j driver
        self.driver = GraphDatabase.driver(self.uri, auth=(self.user, self.password))
        self.semaphore = asyncio.Semaphore(self.max_sessions)  # Limit concurrent sessions

    def close(self):
        self.driver.close()

    @asynccontextmanager
    async def get_session(self):
        async with self.semaphore:  # Acquire a slot from the semaphore
            session = self.driver.session()
            try:
                yield session
            finally:
                session.close()

neo4j_conn = Neo4jConnection()