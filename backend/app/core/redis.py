import os
import redis.asyncio as redis
from app.core.config import settings
from typing import Optional, Union, Any, TypeVar, Generic, Type
from pydantic import BaseModel
import json # For potential serialization
import logging

logger = logging.getLogger(__name__)

T = TypeVar('T')

class RedisConnection:
    def __init__(self, host=None, port=None, db=None, password=None):
        self.host = host or settings.REDIS_HOST
        self.port = port or settings.REDIS_PORT
        self.db = db or settings.REDIS_DB
        self.password = password or settings.REDIS_PASSWORD
        self._pool: Optional[redis.ConnectionPool] = None
        logger.info(f"Redis config initialized with host={self.host}, port={self.port}")

    async def connect(self):
        """Initializes the Redis connection pool."""
        if self._pool:
            return # Already connected
        try:
            logger.info(f"Connecting to Redis at {self.host}:{self.port}...")
            conn_kwargs = {
                "host": self.host,
                "port": self.port,
                "db": self.db,
                "decode_responses": True,
                "max_connections": 10
            }
            
            # Only add password if it's set
            if self.password:
                conn_kwargs["password"] = self.password
                logger.info("Using password authentication for Redis")
            
            self._pool = redis.ConnectionPool(**conn_kwargs)
            
            # Test connection by getting a client and pinging
            client = self.get_client()
            await client.ping()
            logger.info("Successfully connected to Redis.")
        except Exception as e:
            logger.error(f"Error connecting to Redis: {e}")
            self._pool = None
            # Optionally re-raise or handle connection failure
            raise

    async def close(self):
        """Closes the Redis connection pool."""
        if self._pool:
            await self._pool.disconnect()
            self._pool = None # Ensure pool is marked as None after closing
            logger.info("Redis connection pool closed.")

    def get_client(self) -> redis.Redis:
        """Gets a Redis client instance connected to the pool."""
        if not self._pool:
            # Consider connecting automatically or raising a more specific error
            raise RuntimeError("Redis connection pool not initialized. Call connect() first or use lifespan.")
        return redis.Redis(connection_pool=self._pool)

    # --- Easy-to-use methods --- 

    async def get(self, key: str) -> Optional[str]:
        """Gets a value from Redis by key."""
        try:
            client = self.get_client()
            value = await client.get(key)
            return value # Returns None if key doesn't exist
        except Exception as e:
            logger.error(f"Error getting Redis key '{key}': {e}")
            # Decide how to handle errors (return None, raise, etc.)
            return None

    async def set(
        self,
        key: str,
        value: Union[str, int, float, dict, list],
        ttl: Optional[int] = None # TTL in seconds
    ) -> bool:
        """Sets a key-value pair in Redis, optionally with a TTL (in seconds)."""
        try:
            client = self.get_client()
            # Basic serialization for non-string types (consider more robust options if needed)
            if not isinstance(value, (str, bytes)): 
                value_str = json.dumps(value)
            else:
                value_str = value
                
            result = await client.set(key, value_str, ex=ttl)
            return result == True # SET command returns True on success
        except Exception as e:
            logger.error(f"Error setting Redis key '{key}': {e}")
            return False

    async def remove(self, key: str) -> int:
        """Removes a key from Redis. Returns the number of keys removed (0 or 1)."""
        try:
            client = self.get_client()
            result = await client.delete(key)
            return result # Returns number of keys deleted
        except Exception as e:
            logger.error(f"Error removing Redis key '{key}': {e}")
            return 0
            
    # --- Caching methods ---
    
    async def cache_object(self, key: str, obj: Any, ttl_seconds: int) -> bool:
        """Cache any object as JSON with expiration time"""
        try:
            # Convert to dict if it's a Pydantic model or SQLModel
            if hasattr(obj, "model_dump"):
                data = obj.model_dump()
            elif hasattr(obj, "dict"):
                data = obj.dict()
            else:
                data = obj
                
            return await self.set(key, data, ttl=ttl_seconds)
        except Exception as e:
            logger.error(f"Error caching object with key '{key}': {e}")
            return False
            
    async def get_cached_object(self, key: str, model_class: Optional[Type[T]] = None) -> Optional[Union[dict, T]]:
        """Get cached object, optionally converting it to a specific model class"""
        data = await self.get(key)
        if not data:
            return None
            
        try:
            # Parse JSON data
            if isinstance(data, str):
                parsed_data = json.loads(data)
            else:
                parsed_data = data
                
            # Return as the model if requested
            if model_class:
                if isinstance(parsed_data, list):
                    return [model_class(**item) for item in parsed_data]
                return model_class(**parsed_data)
            return parsed_data
        except Exception as e:
            logger.error(f"Error deserializing cached object with key '{key}': {e}")
            return None
            
    async def cache_list(self, key: str, items: list, ttl_seconds: int) -> bool:
        """Cache a list of objects with expiration time"""
        try:
            # Convert list items if they are models
            serializable_items = []
            for item in items:
                if hasattr(item, "model_dump"):
                    serializable_items.append(item.model_dump())
                elif hasattr(item, "dict"):
                    serializable_items.append(item.dict())
                else:
                    serializable_items.append(item)
                    
            return await self.set(key, serializable_items, ttl=ttl_seconds)
        except Exception as e:
            logger.error(f"Error caching list with key '{key}': {e}")
            return False

    # Add these methods to the RedisConnection class in redis.py

    async def lpush(self, key: str, value: str) -> int:
        """Push a value to the head of a Redis list."""
        try:
            client = self.get_client()
            result = await client.lpush(key, value)
            return result  # Returns the length of the list after the push
        except Exception as e:
            logger.error(f"Error pushing to Redis list '{key}': {e}")
            return 0

    async def llen(self, key: str) -> int:
        """Get the length of a Redis list."""
        try:
            client = self.get_client()
            result = await client.llen(key)
            return result
        except Exception as e:
            logger.error(f"Error getting Redis list length for '{key}': {e}")
            return 0

    async def lrange(self, key: str, start: int, end: int) -> list:
        """Get a range of values from a Redis list."""
        try:
            client = self.get_client()
            result = await client.lrange(key, start, end)
            return result
        except Exception as e:
            logger.error(f"Error getting Redis list range for '{key}': {e}")
            return []

    async def ltrim(self, key: str, start: int, end: int) -> bool:
        """Trim a Redis list to the specified range."""
        try:
            client = self.get_client()
            result = await client.ltrim(key, start, end)
            return result
        except Exception as e:
            logger.error(f"Error trimming Redis list '{key}': {e}")
            return False

    async def pipeline(self):
        """Get a Redis pipeline."""
        try:
            client = self.get_client()
            return client.pipeline()
        except Exception as e:
            logger.error(f"Error creating Redis pipeline: {e}")
            raise
# --- Singleton Instance --- 
redis_conn = RedisConnection()

# --- FastAPI Lifespan Integration (Recommended) --- 
# Ensure connect() and close() are called during app startup/shutdown
# Example in main.py:
# 
# from contextlib import asynccontextmanager
# from fastapi import FastAPI
# from app.core.redis import redis_conn # Import the instance
# 
# @asynccontextmanager
# async def lifespan(app: FastAPI):
#     print("Connecting to Redis...")
#     await redis_conn.connect()
#     yield
#     print("Closing Redis connection...")
#     await redis_conn.close()
# 
# app = FastAPI(lifespan=lifespan, ...)
# 