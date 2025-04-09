from fastapi import APIRouter, Depends
from app.api.deps import Neo4jSessionDep
from neo4j import Session
from app.models.neo4j import BlogRecommendation, BlogRequest
from  typing import Any
router = APIRouter(prefix="/neo4j", tags=["neo4j"])

@router.get("/nodes")
async def get_nodes(neo4j_session: Neo4jSessionDep):
    # Example query
    result = neo4j_session.run("MATCH (n) RETURN n LIMIT 10")
    return [dict(record) for record in result]

@router.post("/create-node")
async def create_node(neo4j_session: Neo4jSessionDep, data: dict):
    # Example of creating a node with parameters
    query = """
        CREATE (n:Node {name: $name, properties: $properties})
        RETURN n
    """
    result = neo4j_session.run(query, name=data["name"], properties=data["properties"])
    return dict(result.single())
@router.get("/similarity_thread")
def similarity_post(neo4j_session : Neo4jSessionDep,thread_id:int  )-> Any:
    query = """
     MATCH (t:Thread)-[:HAS_TAG]->(tag:Tag)<-[:HAS_TAG]-(other:Thread)
WHERE t.id = $thread_id AND t <> other
WITH other, COUNT(tag) AS sharedTags
ORDER BY sharedTags DESC
RETURN other.id AS threadId, sharedTags
LIMIT 5
       """
    result = neo4j_session.run(query,thread_id=thread_id)
    recommend=[record["threadId"] for record in result]
    return BlogRecommendation(recommendations=recommend)
@router.post("/add_tag_to_thread")
def add_tag(neo4j_session:Neo4jSessionDep,thread_id:int, tag_name:str)->Any:
    query = """
        MATCH (t:Thread {id: $thread_id})
        MERGE (tag:Tag {name: $tag_name})
        MERGE (t)-[:HAS_TAG]->(tag)
        RETURN t.id AS threadId, tag.name AS tagName
        """
    result =neo4j_session.run(query, thread_id=thread_id, tag_name=tag_name)
    record = result.single()
    if not record:
        raise ValueError("Thread not found")
    return {
            "thread_id": record["threadId"],
            "tag_name": record["tagName"]
        }