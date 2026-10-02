"""
Celery application — runs long jobs (document processing, analysis) outside HTTP requests.

Start a worker (from backend/):
    celery -A app.worker.celery_app worker --loglevel=INFO --concurrency=2

Settings chosen for safety:
- acks_late + reject_on_worker_lost: a task is only removed from the queue after it
  finishes, so a crashed worker's task is redelivered (at-least-once delivery).
  That is why every task is written to be idempotent.
- prefetch_multiplier=1: a worker holds one long task at a time instead of hoarding.
"""
from celery import Celery

from app.core.config import settings

celery_app = Celery("idea_atlas", broker=settings.REDIS_URL, include=["app.tasks"])
celery_app.conf.update(
    task_always_eager=settings.CELERY_TASK_ALWAYS_EAGER,
    task_eager_propagates=True,
    task_acks_late=True,
    task_reject_on_worker_lost=True,
    worker_prefetch_multiplier=1,
    task_serializer="json",
    accept_content=["json"],
    task_ignore_result=True,          # status lives in Postgres, not in a Celery result backend
    broker_connection_retry_on_startup=True,
    task_default_queue="atlas",
)
