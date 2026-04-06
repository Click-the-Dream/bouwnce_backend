from celery import Celery

from app.core.config import settings

celery_app = Celery(
    settings.PROJECT_NAME,
    broker=f"{settings.REDIS_URL}/1",
    include=["app.worker.tasks.email", "app.worker.tasks.order_processor"],
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
)
