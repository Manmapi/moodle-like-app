from fastapi import APIRouter, Depends
from app.api.deps import Neo4jSessionDep
from neo4j import Session

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