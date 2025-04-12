from typing import Any
from neo4j import Session as Neo4jSession



def get_similar_threads(neo4j_session : Neo4jSession, thread_id: int, limit: int = 5)-> dict:
    query = """
        MATCH (t:Thread)-[:HAS_TAG]->(tag:Tag)<-[:HAS_TAG]-(other:Thread)
        WHERE t.id = $thread_id AND t <> other
        WITH other, COUNT(tag) AS sharedTags
        ORDER BY sharedTags DESC
        RETURN other.id AS threadId, sharedTags
        LIMIT $limit
       """
    result = neo4j_session.run(query, thread_id=thread_id, limit=limit)
    return [dict(record) for record in result]


def add_tags_to_thread(thread_id: int, tags: list[str], *, neo4j_session: Neo4jSession):
    # Ensure the Thread node exists using MERGE
    merge_thread_query = """
        MERGE (t:Thread {id: $thread_id})
    """
    neo4j_session.run(merge_thread_query, thread_id=thread_id)

    # For each tag, ensure the Tag node exists and the relationship exists
    for tag_name in tags:
        merge_tag_rel_query = """
            MATCH (t:Thread {id: $thread_id}) 
            MERGE (tag:Tag {name: $tag_name}) 
            MERGE (t)-[:HAS_TAG]->(tag)
        """
        neo4j_session.run(merge_tag_rel_query, thread_id=thread_id, tag_name=tag_name)

    return {"message": "Tags added/merged successfully"}
