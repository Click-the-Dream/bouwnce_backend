from celery import Celery

from app.core.config import settings

celery_app = Celery(
    settings.PROJECT_NAME,
    broker=f"{settings.REDIS_URL}/0",
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
    broker_pool_limit=1,
    broker_transport_options={"max_connections": 1},
    result_backend=None,
    broker_heartbeat=0,
    broker_connection_retry_on_startup=True,
    broker_connection_max_retries=3,
)

celery_app.conf.beat_schedule = {
    "drain-push-queue": {
        "task": "app.worker.tasks.web_push.drain_push_queue",
        "schedule": 5.0,
    },
}
