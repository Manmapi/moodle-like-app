import logging
import asyncio
from sqlmodel import Session
from app.core.db import engine, init_db
from app.core.neo4j import neo4j_conn
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# Initialize and test SQL
def init_sql() -> None:
    with Session(engine) as session:
        init_db(session)
        logger.info("SQL connection test successful")


# Initialize and test Neo4j
async def init_neo4j() -> None:
    async with neo4j_conn.get_session() as session:  # Use async for with generator
        result = session.run("RETURN 'Neo4j connection test successful!' AS message")
        message = [record["message"] for record in result][0]
        logger.info(f"Neo4j test result: {message}")


# Main function to run both
async def main() -> None:
    logger.info("Starting initialization for SQL and Neo4j")

    # Test SQL (synchronous)
    logger.info("Testing SQL connection")
    init_sql()
    logger.info("SQL connection tested successfully")

    # Test Neo4j (asynchronous)
    logger.info("Testing Neo4j connection")
    await init_neo4j()
    logger.info("Neo4j connection tested successfully")


if __name__ == "__main__":
    asyncio.run(main())