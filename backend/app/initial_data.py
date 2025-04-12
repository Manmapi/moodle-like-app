import logging
import asyncio
import uuid # Import uuid for unique key generation
from sqlmodel import Session
from app.core.db import engine, init_db
from app.core.neo4j import neo4j_conn
from app.core.redis import redis_conn # Import redis connection
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# Initialize and test SQL
def init_sql() -> None:
    with Session(engine) as session:
        init_db(session)
        logger.info("SQL connection test successful")


# Initialize and test Neo4j
async def init_neo4j() -> None:
    async with neo4j_conn.get_session() as session: 
        result = await session.run("RETURN 'Neo4j connection test successful!' AS message") # Use await for run
        record = await result.single() # Use await for single()
        message = record["message"]
        logger.info(f"Neo4j test result: {message}")


# Initialize and test Redis
async def init_redis() -> None:
    logger.info("Testing Redis connection...")
    test_key = f"initial_data_test_{uuid.uuid4()}"
    test_value = "redis_ok"
    try:
        await redis_conn.connect() # Connect explicitly for the test
        
        # Test SET
        set_success = await redis_conn.set(test_key, test_value, ttl=60)
        if not set_success:
            raise Exception("Failed to set test key in Redis")
        logger.info(f"Redis SET test successful (key: {test_key})")

        # Test GET
        retrieved_value = await redis_conn.get(test_key)
        if retrieved_value != test_value:
            raise Exception(f"Redis GET test failed. Expected '{test_value}', got '{retrieved_value}'")
        logger.info("Redis GET test successful")

        # Test DELETE
        deleted_count = await redis_conn.remove(test_key)
        if deleted_count != 1:
            raise Exception(f"Redis DELETE test failed. Expected 1 key deleted, got {deleted_count}")
        logger.info("Redis DELETE test successful")
        
        # Optional: Verify deletion
        # verify_value = await redis_conn.get(test_key)
        # if verify_value is not None:
        #     logger.warning(f"Redis key '{test_key}' still exists after delete attempt.")
        
        logger.info("Redis connection tested successfully")

    except Exception as e:
        logger.error(f"Redis connection test failed: {e}")
        # Decide if failure should halt startup
        # raise
    finally:
        # Ensure connection is closed after test, even if connect wasn't called in lifespan
        await redis_conn.close()


# Main function to run all initializations
async def main() -> None:
    logger.info("Starting initialization for SQL, Neo4j, and Redis")

    # Test SQL (synchronous)
    logger.info("Initializing SQL database...")
    init_sql()
    logger.info("SQL database initialized successfully")

    # Test Neo4j (asynchronous)
    logger.info("Testing Neo4j connection...")
    try:
        await init_neo4j()
        logger.info("Neo4j connection tested successfully")
    except Exception as e:
        logger.error(f"Neo4j connection test failed: {e}")
        # Handle or raise if needed

    # Test Redis (asynchronous)
    await init_redis()


if __name__ == "__main__":
    asyncio.run(main())