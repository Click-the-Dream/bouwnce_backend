"""Unit tests for the web push notification implementation.

These tests run without a live database or Redis: the consumer tests mock
``get_async_session`` / ``get_redis_client`` and the service tests mock
``pywebpush.webpush``.
"""

import asyncio
import json
from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, patch

import pytest
from pydantic import ValidationError

from app.models.web_push_subscription import WebPushSubscription
from app.schemas.push_notification import PushSubscriptionIn, PushUnsubscribeIn
from app.service.web_push_service import (
    DeliveryOutcome,
    send_web_push,
    subscription_is_expired,
)
from app.worker.event_system import EventNames, PushNotificationEvent, dispatch_event
from app.worker.tasks.web_push import (
    DLQ_KEY,
    PUSH_QUEUE_KEY,
    _drain_once,
    drain_push_queue,
)

# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------


class TestPushSchemas:
    def test_valid_subscription(self) -> None:
        sub = PushSubscriptionIn(
            endpoint="https://fcm.googleapis.com/fcm/send/abc123",
            keys={"p256dh": "key", "auth": "secret"},
        )
        assert sub.keys.p256dh == "key"
        assert sub.keys.auth == "secret"

    def test_expiration_time_alias(self) -> None:
        sub = PushSubscriptionIn(
            endpoint="https://fcm.googleapis.com/fcm/send/abc123",
            keys={"p256dh": "key", "auth": "secret"},
            expirationTime="2030-01-01T00:00:00Z",
        )
        assert sub.expiration_time is not None
        assert sub.expiration_time.year == 2030

    def test_localhost_endpoint_allowed(self) -> None:
        sub = PushSubscriptionIn(
            endpoint="http://localhost:8080/push/xyz",
            keys={"p256dh": "key", "auth": "secret"},
        )
        assert sub.endpoint.startswith("http://localhost")

    def test_insecure_endpoint_rejected(self) -> None:
        with pytest.raises(ValidationError):
            PushSubscriptionIn(
                endpoint="http://example.com/push/xyz",
                keys={"p256dh": "key", "auth": "secret"},
            )

    def test_missing_keys_rejected(self) -> None:
        with pytest.raises(ValidationError):
            PushSubscriptionIn(endpoint="https://fcm.googleapis.com/fcm/send/x")

    def test_unsubscribe_valid(self) -> None:
        body = PushUnsubscribeIn(endpoint="https://fcm.googleapis.com/fcm/send/abc")
        assert body.endpoint.startswith("https://")

    def test_unsubscribe_rejects_insecure_endpoint(self) -> None:
        with pytest.raises(ValidationError):
            PushUnsubscribeIn(endpoint="http://example.com/push/x")

    def test_oversized_endpoint_rejected(self) -> None:
        with pytest.raises(ValidationError):
            PushSubscriptionIn(
                endpoint="https://x.example/" + "a" * 2100,
                keys={"p256dh": "key", "auth": "secret"},
            )

    def test_oversized_keys_rejected(self) -> None:
        with pytest.raises(ValidationError):
            PushSubscriptionIn(
                endpoint="https://fcm.googleapis.com/fcm/send/x",
                keys={"p256dh": "k" * 600, "auth": "secret"},
            )
        with pytest.raises(ValidationError):
            PushSubscriptionIn(
                endpoint="https://fcm.googleapis.com/fcm/send/x",
                keys={"p256dh": "key", "auth": "s" * 600},
            )

    def test_empty_endpoint_rejected(self) -> None:
        with pytest.raises(ValidationError):
            PushSubscriptionIn(endpoint="x", keys={"p256dh": "key", "auth": "secret"})


# ---------------------------------------------------------------------------
# Service: expiration + send outcome mapping
# ---------------------------------------------------------------------------


class TestSubscriptionIsExpired:
    def _sub(self, expiration_time) -> WebPushSubscription:
        return WebPushSubscription(
            endpoint="https://push.example/x",
            p256dh="key",
            auth="secret",
            expiration_time=expiration_time,
        )

    def test_none_never_expired(self) -> None:
        assert subscription_is_expired(self._sub(None)) is False

    def test_past_expiration_is_expired(self) -> None:
        past = datetime.now(UTC) - timedelta(minutes=1)
        assert subscription_is_expired(self._sub(past)) is True

    def test_future_expiration_not_expired(self) -> None:
        future = datetime.now(UTC) + timedelta(hours=1)
        assert subscription_is_expired(self._sub(future)) is False


class FakeResponse:
    def __init__(self, status_code: int) -> None:
        self.status_code = status_code


class TestSendWebPush:
    def _sub(self) -> WebPushSubscription:
        return WebPushSubscription(
            endpoint="https://fcm.googleapis.com/fcm/send/abc",
            p256dh="key",
            auth="secret",
        )

    def _exception(self, status_code: int) -> Exception:
        from pywebpush import WebPushException

        return WebPushException("boom", response=FakeResponse(status_code))

    def test_success(self) -> None:
        with patch("app.service.web_push_service.webpush") as mock_send:
            outcome = send_web_push(self._sub(), title="Hi", body="There")
        assert outcome.delivered is True
        assert outcome.expired is False
        assert outcome.retry is False
        mock_send.assert_called_once()

    def test_404_marks_expired(self) -> None:
        with patch(
            "app.service.web_push_service.webpush",
            side_effect=self._exception(404),
        ):
            outcome = send_web_push(self._sub(), title="Hi", body="There")
        assert outcome.delivered is False
        assert outcome.expired is True
        assert outcome.retry is False

    def test_410_marks_expired(self) -> None:
        with patch(
            "app.service.web_push_service.webpush",
            side_effect=self._exception(410),
        ):
            outcome = send_web_push(self._sub(), title="Hi", body="There")
        assert outcome.expired is True

    def test_429_marks_retry(self) -> None:
        with patch(
            "app.service.web_push_service.webpush",
            side_effect=self._exception(429),
        ):
            outcome = send_web_push(self._sub(), title="Hi", body="There")
        assert outcome.delivered is False
        assert outcome.retry is True
        assert outcome.expired is False

    def test_503_marks_retry(self) -> None:
        with patch(
            "app.service.web_push_service.webpush",
            side_effect=self._exception(503),
        ):
            outcome = send_web_push(self._sub(), title="Hi", body="There")
        assert outcome.retry is True

    def test_other_http_error_is_plain_failure(self) -> None:
        with patch(
            "app.service.web_push_service.webpush",
            side_effect=self._exception(400),
        ):
            outcome = send_web_push(self._sub(), title="Hi", body="There")
        assert outcome.delivered is False
        assert outcome.expired is False
        assert outcome.retry is False
        assert outcome.error is not None

    def test_unexpected_exception_is_plain_failure(self) -> None:
        with patch(
            "app.service.web_push_service.webpush",
            side_effect=RuntimeError("network down"),
        ):
            outcome = send_web_push(self._sub(), title="Hi", body="There")
        assert outcome.delivered is False
        assert outcome.error is not None


# ---------------------------------------------------------------------------
# Consumer: _drain_once
# ---------------------------------------------------------------------------


class FakeRedis:
    """Minimal stand-in: FIFO lpop + recorded rpush (by key)."""

    def __init__(self, items: list[str] | None = None) -> None:
        self.items = list(items or [])
        self.pushed: list[tuple[str, str]] = []
        self.streams: list[tuple[str, dict]] = []

    async def lpop(self, _key: str) -> str | None:
        if not self.items:
            return None
        return self.items.pop(0)

    async def rpush(self, key: str, value: str) -> None:
        self.pushed.append((key, value))

    async def xadd(self, key: str, fields: dict, **kwargs) -> None:
        self.streams.append((key, fields))

    @property
    def requeued(self) -> list[str]:
        return [v for k, v in self.pushed if k == PUSH_QUEUE_KEY]


class FakeSession:
    """Async context manager whose inner value is a dummy db object."""

    def __init__(self) -> None:
        self._db = object()

    async def __aenter__(self):
        return self._db

    async def __aexit__(self, *_args) -> None:
        return None


def _payload(user_id: str, **extra) -> str:
    data = {"user_id": user_id, "title": "T", "body": "B", **extra}
    return json.dumps(data)


class TestDrainOnce:
    def _patch_env(self, redis: FakeRedis):
        stack = [
            patch(
                "app.worker.tasks.web_push.get_redis_client",
                AsyncMock(return_value=redis),
            ),
            patch(
                "app.worker.tasks.web_push.get_async_session",
                lambda: FakeSession(),
            ),
        ]
        return stack

    async def _run(
        self, redis: FakeRedis, **classmethod_sides
    ) -> tuple[int, AsyncMock, AsyncMock]:
        stacks = self._patch_env(redis)
        list_mock = AsyncMock()
        delete_mock = AsyncMock()
        list_mock.side_effect = classmethod_sides.get("list_for_user", [])
        delete_mock.side_effect = classmethod_sides.get("delete_by_endpoint", [True])
        stacks.append(
            patch(
                "app.worker.tasks.web_push.WebPushSubscription.list_for_user",
                list_mock,
            )
        )
        stacks.append(
            patch(
                "app.worker.tasks.web_push.WebPushSubscription.delete_by_endpoint",
                delete_mock,
            )
        )
        for s in stacks:
            s.start()
        try:
            processed = await _drain_once()
        finally:
            for s in stacks:
                s.stop()
        return processed, list_mock, delete_mock

    def test_empty_queue_returns_zero(self) -> None:
        processed, _, _ = self._run_sync(FakeRedis())
        assert processed == 0

    def test_malformed_payload_skipped(self) -> None:
        redis = FakeRedis(["not-json{"])
        processed, list_mock, _ = self._run_sync(redis)
        assert processed == 1  # the item was consumed
        list_mock.assert_not_called()

    def _run_sync(self, redis: FakeRedis, **sides):
        return asyncio.run(self._run(redis, **sides))

    def test_bad_user_id_skipped(self) -> None:
        redis = FakeRedis([_payload("not-a-uuid")])
        processed, list_mock, _ = self._run_sync(redis)
        assert processed == 1
        list_mock.assert_not_called()

    def test_user_without_subscriptions_skipped(self) -> None:
        redis = FakeRedis([_payload("11111111-1111-1111-1111-111111111111")])
        processed, _, _ = self._run_sync(redis, list_for_user=[[]])
        assert processed == 1

    def test_delivered_subscription(self) -> None:
        sub = WebPushSubscription(
            endpoint="https://push.example/x", p256dh="k", auth="s"
        )
        redis = FakeRedis([_payload("11111111-1111-1111-1111-111111111111")])
        with patch(
            "app.worker.tasks.web_push.send_web_push",
            return_value=DeliveryOutcome(delivered=True),
        ) as send_mock:
            processed, _, delete_mock = self._run_sync(redis, list_for_user=[[sub]])
        assert processed == 1
        send_mock.assert_called_once()
        delete_mock.assert_not_called()
        assert redis.requeued == []

    def test_expired_subscription_pruned(self) -> None:
        past = datetime.now(UTC) - timedelta(minutes=1)
        sub = WebPushSubscription(
            endpoint="https://push.example/x",
            p256dh="k",
            auth="s",
            expiration_time=past,
        )
        redis = FakeRedis([_payload("11111111-1111-1111-1111-111111111111")])
        processed, _, delete_mock = self._run_sync(
            redis, list_for_user=[[sub]], delete_by_endpoint=[True]
        )
        assert processed == 1
        delete_mock.assert_called_once()

    def test_gone_subscription_removed(self) -> None:
        sub = WebPushSubscription(
            endpoint="https://push.example/x", p256dh="k", auth="s"
        )
        redis = FakeRedis([_payload("11111111-1111-1111-1111-111111111111")])
        with patch(
            "app.worker.tasks.web_push.send_web_push",
            return_value=DeliveryOutcome(expired=True, error="gone"),
        ):
            processed, _, delete_mock = self._run_sync(
                redis, list_for_user=[[sub]], delete_by_endpoint=[True]
            )
        assert processed == 1
        delete_mock.assert_called_once()

    def test_retry_requeued_after_batch(self) -> None:
        sub = WebPushSubscription(
            endpoint="https://push.example/x", p256dh="k", auth="s"
        )
        redis = FakeRedis([_payload("11111111-1111-1111-1111-111111111111")])
        with patch(
            "app.worker.tasks.web_push.send_web_push",
            return_value=DeliveryOutcome(retry=True, error="429"),
        ):
            processed, _, _ = self._run_sync(redis, list_for_user=[[sub]])
        assert processed == 1
        assert len(redis.requeued) == 1
        assert redis.requeued[0] == _payload("11111111-1111-1111-1111-111111111111")

    def test_retry_breaks_and_skips_remaining_subscriptions(self) -> None:
        # A user with several browsers: if the first subscription rate-limits,
        # the remaining ones are NOT attempted this run and the payload is
        # requeued once (documented behavior of _drain_once).
        first = WebPushSubscription(
            endpoint="https://push.example/1", p256dh="k", auth="s"
        )
        second = WebPushSubscription(
            endpoint="https://push.example/2", p256dh="k", auth="s"
        )
        redis = FakeRedis([_payload("11111111-1111-1111-1111-111111111111")])
        with patch(
            "app.worker.tasks.web_push.send_web_push",
            return_value=DeliveryOutcome(retry=True, error="429"),
        ) as send_mock:
            processed, _, delete_mock = self._run_sync(
                redis, list_for_user=[[first, second]]
            )
        assert processed == 1
        assert send_mock.call_count == 1  # second subscription never attempted
        delete_mock.assert_not_called()
        assert len(redis.requeued) == 1

    def test_permanent_failure_goes_to_dlq(self) -> None:
        sub = WebPushSubscription(
            endpoint="https://push.example/x", p256dh="k", auth="s"
        )
        payload = _payload("11111111-1111-1111-1111-111111111111")
        redis = FakeRedis([payload])
        with patch(
            "app.worker.tasks.web_push.send_web_push",
            return_value=DeliveryOutcome(error="bad key"),
        ):
            processed, _, _ = self._run_sync(redis, list_for_user=[[sub]])
        assert processed == 1
        assert redis.requeued == []
        assert DLQ_KEY in [k for k, _ in redis.pushed]
        assert [v for k, v in redis.pushed if k == DLQ_KEY] == [payload]

    def test_max_per_run_cap(self) -> None:
        # 120 items queued, but only MAX_PER_RUN (100) are processed per run.
        # Valid UUIDs -> list_for_user is called per payload; it finds no subs.
        items = [
            _payload(f"11111111-1111-1111-1111-1111111111{i:02d}") for i in range(120)
        ]
        redis = FakeRedis(items)
        processed, list_mock, _ = self._run_sync(
            redis, list_for_user=[[] for _ in range(120)]
        )
        assert processed == 100
        assert list_mock.await_count == 100


# ---------------------------------------------------------------------------
# Celery task wrapper
# ---------------------------------------------------------------------------


class TestDrainTask:
    def test_returns_processed_count(self) -> None:
        with patch(
            "app.worker.tasks.web_push._drain_once",
            new_callable=AsyncMock,
            return_value=3,
        ):
            assert drain_push_queue() == 3

    def test_returns_zero_when_drain_raises(self) -> None:
        with patch(
            "app.worker.tasks.web_push._drain_once",
            new_callable=AsyncMock,
            side_effect=RuntimeError("redis down"),
        ):
            assert drain_push_queue() == 0


class TestBeatSchedule:
    """The production trigger: Celery beat must wire the drain task."""

    def test_beat_schedule_wires_drain_task(self) -> None:
        from app.worker.celery_app import celery_app

        schedule = celery_app.conf.beat_schedule
        assert "drain-push-queue" in schedule
        entry = schedule["drain-push-queue"]
        assert entry["task"] == "app.worker.tasks.web_push.drain_push_queue"
        assert entry["schedule"] == 5.0

    def test_task_registered_on_celery_app(self) -> None:
        from app.worker.celery_app import celery_app

        assert (
            celery_app.tasks.get("app.worker.tasks.web_push.drain_push_queue")
            is not None
        )


# ---------------------------------------------------------------------------
# Producer: dispatch_event (PUSH_NOTIFICATION)
# ---------------------------------------------------------------------------


class TestDispatchPushEvent:
    @staticmethod
    def _dispatch(data_type: str | None = None):
        fake = FakeRedis()
        data = {"type": data_type} if data_type else {}
        with patch(
            "app.worker.event_system.Notification.create",
            new_callable=AsyncMock,
        ) as notif_mock:
            asyncio.run(
                dispatch_event(
                    EventNames.PUSH_NOTIFICATION,
                    PushNotificationEvent(
                        user_id="u-1", title="T", body="B", data=data
                    ),
                    db=object(),
                    redis=fake,
                )
            )
        return fake, notif_mock

    @staticmethod
    def _queue_items(fake: FakeRedis) -> list[str]:
        return [v for k, v in fake.pushed if k == "notifications:push:queue"]

    def test_persists_and_enqueues_payload(self) -> None:
        fake, notif_mock = self._dispatch("order.confirmed")
        notif_mock.assert_awaited_once()
        items = self._queue_items(fake)
        assert len(items) == 1
        assert json.loads(items[0]) == {
            "user_id": "u-1",
            "title": "T",
            "body": "B",
            "data": {"type": "order.confirmed"},
        }
        # mobile stream published
        assert len(fake.streams) == 1
        assert fake.streams[0][0] == "events:mobile:stream"

    def test_defaults_empty_data(self) -> None:
        fake, notif_mock = self._dispatch(None)
        notif_mock.assert_awaited_once()
        assert json.loads(self._queue_items(fake)[0])["data"] == {}

    def test_chat_type_skips_db_persist(self) -> None:
        fake, notif_mock = self._dispatch("chat.message")
        notif_mock.assert_not_awaited()
        assert len(self._queue_items(fake)) == 1  # still enqueued

    def test_match_type_skips_db_persist(self) -> None:
        fake, notif_mock = self._dispatch("match.new")
        notif_mock.assert_not_awaited()

    def test_missing_redis_raises(self) -> None:
        with pytest.raises(ValueError):
            asyncio.run(
                dispatch_event(
                    EventNames.PUSH_NOTIFICATION,
                    PushNotificationEvent(user_id="u-1", title="T", body="B", data={}),
                    db=object(),
                    redis=None,
                )
            )
