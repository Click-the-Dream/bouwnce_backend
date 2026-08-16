import asyncio
from typing import Any

from app.db.postgres_db_conn import get_async_session
from app.service.web_push_service import web_push_service
from app.worker.celery_app import celery_app


@celery_app.task(name="app.worker.tasks.web_push.send_web_push")
def send_web_push(
    user_id: str, title: str, body: str, data: dict[str, Any]
) -> dict[str, Any]:
    """Best-effort browser push for a user.

    No-op (returns ``{"skipped": True}``) when VAPID is not configured. Stale
    subscriptions are pruned as a side effect.
    """

    async def _run() -> dict[str, Any]:
        async with get_async_session() as db:
            return await web_push_service.send_to_user(
                db=db, user_id=user_id, title=title, body=body, data=data
            )

    return asyncio.run(_run())
