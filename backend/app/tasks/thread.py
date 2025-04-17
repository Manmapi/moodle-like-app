from datetime import datetime
from sqlmodel import text

from app.core.redis import RedisConnection
from app.worker import celery
from app.core.db import engine


@celery.task
def record_thread_view(thread_id: int):
  """Record a single thread view in Redis for later batch processing"""
  import time
  import asyncio

  # Create async function
  async def async_record():
    task_redis = RedisConnection()
    await task_redis.connect()

    # Use Redis list to accumulate views
    key = "thread_views_queue"
    view_data = f"{thread_id}:{int(time.time())}"
    print("Got a task: ", view_data)

    await task_redis.lpush(key, view_data)

    # Check queue length - process if we have enough items
    count = await task_redis.llen(key)
    # Clean up connection before scheduling next task
    await task_redis.close()

    if count >= 100:  # Process in batches of 100
      process_thread_views.delay()
    # For the first item, schedule processing after a delay
    elif count == 1:
      process_thread_views.apply_async(countdown=60)  # Process after 1 minute

  # Run the async function in a new event loop
  loop = asyncio.new_event_loop()
  asyncio.set_event_loop(loop)
  try:
    return loop.run_until_complete(async_record())
  finally:
    loop.close()


@celery.task
def process_thread_views():
  """Process accumulated thread views in batch"""
  import asyncio
  from app.models.thread import ThreadView
  from sqlmodel import Session
  from app.core.db import engine

  # Create async function
  async def async_process():
    # Create a fresh connection for this task
    task_redis = RedisConnection()
    await task_redis.connect()

    key = "thread_views_queue"

    # Get items from the list
    items = await task_redis.lrange(key, -1000, -1)

    # Trim the list
    await task_redis.ltrim(key, 0, -1001)

    # Close the Redis connection
    await task_redis.close()

    if not items:
      return "No views to process"

    views = []
    for item in items:
      thread_id, timestamp = item.split(":")
      created_at = datetime.fromtimestamp(int(timestamp))
      views.append((int(thread_id), created_at))

    # Batch insert to database
    with Session(engine) as session:
      thread_views = [
        ThreadView(thread_id=thread_id, created_at=created_at)
        for thread_id, created_at in views
      ]
      session.add_all(thread_views)
      session.commit()

    return f"Processed {len(views)} thread views in batch"

  # Run the async function in a new event loop
  loop = asyncio.new_event_loop()
  asyncio.set_event_loop(loop)
  try:
    return loop.run_until_complete(async_process())
  finally:
    loop.close()

def create_trending_threads_materialized_view():
    """
    Create a materialized view for trending threads.
    This should be run once during database setup.
    """
    query = """
    CREATE MATERIALIZED VIEW IF NOT EXISTS trending_threads AS
    WITH
    day_views AS (
        SELECT
            thread_id,
            COUNT(*) as day_count
        FROM
            threadview
        WHERE
            created_at > NOW() - INTERVAL '1 day'
        GROUP BY
            thread_id
    ),
    week_views AS (
        SELECT
            thread_id,
            COUNT(*) as week_count
        FROM
            threadview
        WHERE
            created_at > NOW() - INTERVAL '7 days'
        GROUP BY
            thread_id
    ),
    month_views AS (
        SELECT
            thread_id,
            COUNT(*) as month_count
        FROM
            threadview
        WHERE
            created_at > NOW() - INTERVAL '30 days'
        GROUP BY
            thread_id
    )
    SELECT
        t.id,
        COALESCE(d.day_count, 0) * 5 +
        COALESCE(w.week_count, 0) * 2 +
        COALESCE(m.month_count, 0) AS trending_score
    FROM
        thread t
    LEFT JOIN
        day_views d ON t.id = d.thread_id
    LEFT JOIN
        week_views w ON t.id = w.thread_id
    LEFT JOIN
        month_views m ON t.id = m.thread_id
    ORDER BY
        trending_score DESC
    LIMIT 10;

    CREATE UNIQUE INDEX IF NOT EXISTS trending_threads_id_idx ON trending_threads (id);
    """

    with engine.connect() as conn:
        conn.execute(text(query))
        conn.commit()

@celery.task
def refresh_trending_view():
    """
    Celery task to refresh the trending threads materialized view.
    Schedule this to run periodically (e.g., hourly).
    """
    query = "REFRESH MATERIALIZED VIEW trending_threads;"
    with engine.connect() as conn:
        conn.execute(text(query))
        conn.commit()
    return "Trending threads view refreshed"