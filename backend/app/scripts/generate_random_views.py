import random
import asyncio
from datetime import datetime, timedelta
from sqlmodel import Session, select
from app.core.db import engine
from app.models.thread import Thread, ThreadView


async def generate_random_views(total_views=1000):
  """
  Generate random views for threads to populate the trending data.

  Args:
      total_views: Total number of views to generate across all threads
  """
  print(f"Generating {total_views} random thread views...")

  # Get all threads from the database
  with Session(engine) as session:
    threads = session.exec(select(Thread)).all()

    if not threads:
      print("No threads found in the database")
      return

    thread_ids = [thread.id for thread in threads]

  # Configure view distribution
  now = datetime.now()
  thirty_days_ago = now - timedelta(days=30)

  # Create thread views directly in the database
  with Session(engine) as session:
    batch_size = 100
    view_count = 0
    batch = []

    for _ in range(total_views):
      # Select a random thread
      thread_id = random.choice(thread_ids)

      # Generate a random timestamp between now and 30 days ago
      # Weight more recent dates higher for realistic trending data
      days_ago = random.betavariate(1, 3) * 30  # Beta distribution favors recent dates
      view_date = now - timedelta(days=days_ago)

      # Create a ThreadView object
      view = ThreadView(thread_id=thread_id, created_at=view_date)
      batch.append(view)
      view_count += 1

      # Process in batches for efficiency
      if len(batch) >= batch_size:
        session.add_all(batch)
        session.commit()
        print(f"Added {len(batch)} views (total: {view_count}/{total_views})")
        batch = []

    # Add any remaining views
    if batch:
      session.add_all(batch)
      session.commit()
      print(f"Added {len(batch)} views (total: {view_count}/{total_views})")

  print(f"Successfully generated {total_views} random thread views")
  print("Refreshing trending threads materialized view...")

  # Refresh the materialized view
  from app.tasks.thread import refresh_trending_view
  refresh_trending_view.delay()

  print("View generation complete!")


if __name__ == "__main__":
  # Configure the number of views to generate
  TOTAL_VIEWS = 10000  # Adjust as needed

  # Run the async function
  asyncio.run(generate_random_views(TOTAL_VIEWS))