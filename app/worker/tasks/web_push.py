import asyncio
import json
import logging
from uuid import UUID

from app.db.postgres_db_conn import get_async_session
from app.db.redis import get_redis_client
from app.models.web_push_subscription import WebPushSubscription
from app.service.web_push_service import (
    send_web_push,
    subscription_is_expired,
)
from app.worker.celery_app import celery_app

logger = logging.getLogger(__name__)

PUSH_QUEUE_KEY = "notifications:push:queue"
DLQ_KEY = "dlq:web_push"  # permanently undeliverable payloads, for manual replay
MAX_PER_RUN = 100  # hard cap on items processed per task run
SEND_DELAY_SECONDS = 0.05  # gentle pacing to avoid push-service rate limits


async def _drain_once() -> int:
    """Pop queued push payloads and deliver them to web subscriptions.

    Payload shape (produced by ``dispatch_event`` PUSH_NOTIFICATION):
    {"user_id": str, "title": str, "body": str, "data": dict}

    Delivery semantics:
    - 404/410 from the push service -> subscription removed from the DB.
    - 429/5xx -> payload requeued once after the batch; a retry also stops
      sending to the user's remaining subscriptions this run (a rate-limited
      endpoint is not hammered, at the cost of delaying the rest).
    - Permanent failures -> payload moved to ``dlq:web_push`` for replay.
    """
    redis = await get_redis_client()
    processed = 0
    retry_payloads: list[str] = []

    async with get_async_session() as db:
        for _ in range(MAX_PER_RUN):
            raw = await redis.lpop(PUSH_QUEUE_KEY)
            if raw is None:
                break
            processed += 1

            try:
                payload = json.loads(raw)
            except (TypeError, json.JSONDecodeError):
                logger.warning("Skipping malformed push payload: %r", raw[:200])
                continue

            user_id = payload.get("user_id")
            title = payload.get("title") or "Notification"
            body = payload.get("body") or ""
            data = payload.get("data") or {}
            event_type = (data or {}).get("type", "unknown")

            try:
                user_uuid = UUID(str(user_id))
            except (ValueError, TypeError):
                logger.warning("Skipping push payload with bad user_id: %r", user_id)
                continue

            logger.info(
                "Processing push for user=%s event=%s title=%r body_preview=%r",
                user_id,
                event_type,
                title,
                body[:80],
            )

            subscriptions = await WebPushSubscription.list_for_user(db, user_uuid)
            if not subscriptions:
                logger.warning(
                    "No push subscriptions found for user=%s, skipping", user_id
                )
                continue

            logger.info(
                "Found %d subscription(s) for user=%s", len(subscriptions), user_id
            )

            requeued = False
            delivered_count = 0
            failed_count = 0
            for subscription in subscriptions:
                if subscription_is_expired(subscription):
                    # Browser said this subscription expires before now: prune it.
                    await WebPushSubscription.delete_by_endpoint(
                        db,
                        user_id=user_uuid,
                        endpoint=subscription.endpoint,
                    )
                    logger.info(
                        "Pruned expired web push subscription %s for user=%s",
                        subscription.endpoint,
                        user_id,
                    )
                    failed_count += 1
                    continue

                outcome = send_web_push(subscription, title=title, body=body, data=data)
                if outcome.expired:
                    # Push service reports the subscription is gone.
                    await WebPushSubscription.delete_by_endpoint(
                        db,
                        user_id=user_uuid,
                        endpoint=subscription.endpoint,
                    )
                    logger.info(
                        "Removed expired web push subscription %s for user=%s",
                        subscription.endpoint,
                        user_id,
                    )
                    failed_count += 1
                elif outcome.retry:
                    # Transient failure: requeue once after the batch finishes so
                    # we do not hammer the rate-limited push service in this run.
                    retry_payloads.append(raw)
                    requeued = True
                    logger.warning(
                        "Transient failure (retry) for user=%s endpoint=%s: %s",
                        user_id,
                        subscription.endpoint,
                        outcome.error,
                    )
                    break
                elif not outcome.delivered:
                    # Permanent failure (bad keys, bad VAPID config, network
                    # error): park it on the DLQ so it is observable/replayable
                    # instead of silently dropping the notification.
                    await redis.rpush(DLQ_KEY, raw)
                    logger.error(
                        "Push DELIVERY FAILED for user=%s endpoint=%s, moved to DLQ: %s",
                        user_id,
                        subscription.endpoint,
                        outcome.error,
                    )
                    failed_count += 1
                else:
                    delivered_count += 1
                    logger.info(
                        "Push DELIVERED for user=%s endpoint=%s",
                        user_id,
                        subscription.endpoint,
                    )
                await asyncio.sleep(SEND_DELAY_SECONDS)

            logger.info(
                "Push result for user=%s event=%s: delivered=%d failed=%d requeued=%s",
                user_id,
                event_type,
                delivered_count,
                failed_count,
                requeued,
            )

            if requeued:
                logger.warning("Requeued push for %s (transient failure)", user_id)

    # Requeue transient failures once, at the tail, after the batch completes.
    if retry_payloads:
        logger.info(
            "Requeuing %d transient failure(s) to the push queue", len(retry_payloads)
        )
    for raw in retry_payloads:
        await redis.rpush(PUSH_QUEUE_KEY, raw)

    return processed


@celery_app.task(name="app.worker.tasks.web_push.drain_push_queue")
def drain_push_queue() -> int:
    """Celery task: deliver pending web push notifications."""
    try:
        processed = asyncio.run(_drain_once())
        if processed:
            logger.info("Push queue drained: %d item(s) processed", processed)
        else:
            logger.debug("Push queue is empty, nothing to process")
        return processed
    except Exception as exc:  # noqa: BLE001 - keep the worker alive on infra errors
        logger.error("Push queue drain failed: %s", exc)
        return 0
