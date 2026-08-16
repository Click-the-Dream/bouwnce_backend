from celery import Celery

from app.core.config import settings

celery_app = Celery(
    settings.PROJECT_NAME,
    broker=f"{settings.REDIS_URL}/1",
    include=[
        "app.worker.tasks.email",
        "app.worker.tasks.order_processor",
        "app.worker.tasks.web_push",
    ],
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_always_eager=settings.CELERY_ALWAYS_EAGER,
    task_eager_propagates=settings.CELERY_ALWAYS_EAGER,
)

# Deliver pending web push notifications every 5 seconds.
# Requires a beat scheduler to be running (e.g. `celery -A app.worker.celery_app.celery_app beat`).
celery_app.conf.beat_schedule = {
    "drain-push-queue": {
        "task": "app.worker.tasks.web_push.drain_push_queue",
        "schedule": 5.0,
    },
}
