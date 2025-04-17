from celery import Celery
from app.core.config import settings

# Configure Celery
celery = Celery(
    "worker",
    broker=f"redis://:{settings.REDIS_PASSWORD}@{settings.REDIS_HOST}:{settings.REDIS_PORT}/{settings.REDIS_DB}",
    backend=f"redis://:{settings.REDIS_PASSWORD}@{settings.REDIS_HOST}:{settings.REDIS_PORT}/{settings.REDIS_DB}",
    include=["app.tasks"],
)

celery.conf.task_routes = {"app.app.tasks.*": {"queue": "main-queue"}}
celery.conf.beat_schedule = {
    'refresh-trending-view': {
        'task': 'app.tasks.thread.refresh_trending_view',
        'schedule': 3600.0,  # Refresh every hour
    },
}

# Optional: Configure other Celery settings
celery.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
)

# Create a sample task for testing
@celery.task
def example_task(name: str) -> str:
    print("Running example task with name:", name)
    return f"Hello {name}"
