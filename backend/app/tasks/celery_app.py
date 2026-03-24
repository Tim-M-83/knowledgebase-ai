from celery import Celery

from app.core.config import get_settings
from app.core.logging_setup import configure_app_logging


settings = get_settings()
configure_app_logging('worker')

celery_app = Celery(
    'knowledgebase_tasks',
    broker=settings.redis_url,
    backend=settings.redis_url,
    include=['app.tasks.ingestion_tasks'],
)
celery_app.conf.task_always_eager = settings.celery_task_always_eager
