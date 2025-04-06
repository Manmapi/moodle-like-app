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
@router.get("/similarity_post")
def similarity_post(neo4j_session : Neo4jSessionDep,post_id:int  )-> Any:
    query = """
       MATCH (b:Blog)-[:HAS_TAG|:HAS_CATEGORY]->(c)<-[:HAS_TAG|:HAS_CATEGORY]-(similar:Blog)
       WHERE b.id = $blog_id AND b <> similar
       RETURN similar.id AS blog_id, COUNT(c) AS score
       ORDER BY score DESC, rand()
       LIMIT 5
       """
    result = neo4j_session.run(query,blog_id=post_id)
    recommend=[record["blog_id"] for record in result]
    return BlogRecommendation(recommendations=recommend)
