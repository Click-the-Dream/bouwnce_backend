"""End-to-end tests for the web push feature.

These run against the REAL FastAPI app, REAL Postgres and REAL Redis. The only
mocked component is ``send_web_push``'s network call to the browser push
service (impossible to do for real without a live browser subscription).

Each test runs inside a single ``asyncio.run`` event loop and boots the app
via ``app.router.lifespan_context`` so the singleton engine/redis pools are
created and used inside the same loop. All test-created state (users,
subscriptions, notifications, rate-limit keys, queue, DLQ) is cleaned up.
"""

import asyncio
import json
from datetime import UTC, datetime, timedelta
from unittest.mock import patch
from uuid import uuid4

import httpx
from httpx import ASGITransport
from sqlalchemy import text

from app.core.config import settings
from app.core.rate_limiter import rate_limiter
from app.core.security import create_token
from app.db.postgres_db_conn import engine, get_async_session
from app.db.redis import close_redis_client, get_redis_client
from app.models.user import User
from app.models.web_push_subscription import WebPushSubscription
from app.service.web_push_service import DeliveryOutcome
from app.worker.tasks.web_push import DLQ_KEY, PUSH_QUEUE_KEY, _drain_once
from main import app

API = "/api/v1/push"
BASE_URL = "http://testserver"


def _endpoint(suffix: str) -> str:
    return f"https://fcm.googleapis.com/fcm/send/e2e-{uuid4().hex[:8]}-{suffix}"


def _sub_payload(endpoint: str) -> dict:
    return {
        "endpoint": endpoint,
        "keys": {
            "p256dh": "key-" + endpoint[-8:],
            "auth": "auth-" + endpoint[-8:],
        },
    }


class E2EBase:
    def run(self, coro):
        return asyncio.run(coro)

    async def _flush_redis_state(self):
        redis = await get_redis_client()
        keys = []
        async for key in redis.scan_iter("rl:*"):
            keys.append(key)
        if keys:
            await redis.delete(*keys)
        await redis.delete(PUSH_QUEUE_KEY, DLQ_KEY)

    async def _create_user(self, db) -> User:
        # ``is_store_owner`` is passed explicitly because the dev DB column has
        # no server default (the model declares one); auth_service does the same.
        return await User.create(
            {
                "email": f"e2e_push_{uuid4().hex[:12]}@bouwnce.test",
                "full_name": "E2E Push Tester",
                "role": "user",
                "is_store_owner": False,
            },
            db,
        )

    @staticmethod
    def _auth(user: User) -> dict[str, str]:
        return {"Authorization": f"Bearer {create_token(str(user.id))}"}

    async def _cleanup(self, db, users: list[User]):
        # Raw SQL deletes: ORM delete of a detached User clashes with the
        # identity map because WebPushSubscription.user is lazy="joined"
        # (loading subscriptions also loads User rows into the session).
        for user in users:
            await db.execute(
                text("DELETE FROM notifications WHERE user_id = :uid"),
                {"uid": user.id},
            )
            await db.execute(
                text("DELETE FROM web_push_subscriptions WHERE user_id = :uid"),
                {"uid": user.id},
            )
            await db.execute(
                text("DELETE FROM users WHERE id = :uid"),
                {"uid": user.id},
            )
        await db.flush()

    async def _scenario_http(self, fn):
        """Run the real app (ASGI) against real Postgres/Redis in one loop.

        Only the rate limiter is initialized (it needs Redis). The full
        ``fastapi_lifespan`` is deliberately NOT used: the push API never
        touches Mongo or the APScheduler, and those module singletons bind to
        the first event loop that uses them, breaking multi-test runs.
        """
        await self._flush_redis_state()
        try:
            await rate_limiter.init()
            async with httpx.AsyncClient(
                transport=ASGITransport(app=app), base_url=BASE_URL
            ) as client:
                await fn(client)
        finally:
            await close_redis_client()
            await engine.dispose()

    async def _scenario_db(self, fn):
        """Run ``fn()`` with services only (no HTTP), one event loop."""
        await self._flush_redis_state()
        try:
            await fn()
        finally:
            await close_redis_client()
            await engine.dispose()


class TestPushApiE2E(E2EBase):
    def test_health_and_vapid_public_key(self):
        async def fn(client):
            health = await client.get("/api/health")
            assert health.status_code == 200
            assert health.json() == {"status": "healthy"}

            resp = await client.get(f"{API}/vapid-public-key")
            assert resp.status_code == 200
            body = resp.json()
            assert body["status"] == "success"
            assert body["status_code"] == 200
            assert body["data"]["public_key"] == settings.VAPID_PUBLIC_KEY
            assert body["data"]["public_key"]  # non-empty

        self.run(self._scenario_http(fn))

    def test_vapid_key_missing_returns_400(self):
        async def fn(client):
            with patch.object(settings, "VAPID_PUBLIC_KEY", ""):
                resp = await client.get(f"{API}/vapid-public-key")
            assert resp.status_code == 400
            assert "not configured" in resp.json()["detail"]["message"]

        self.run(self._scenario_http(fn))

    def test_subscribe_requires_auth(self):
        async def fn(client):
            resp = await client.post(
                f"{API}/subscribe", json=_sub_payload(_endpoint("auth"))
            )
            assert resp.status_code == 401  # HTTPBearer auto-error

            resp = await client.request(
                "DELETE", f"{API}/subscribe", json={"endpoint": _endpoint("auth")}
            )
            assert resp.status_code == 401

        self.run(self._scenario_http(fn))

    def test_subscribe_validation_errors(self):
        async def fn(client):
            async with get_async_session() as db:
                user = await self._create_user(db)
            headers = self._auth(user)

            # insecure endpoint scheme
            resp = await client.post(
                f"{API}/subscribe",
                json={
                    "endpoint": "http://insecure.example/x",
                    "keys": {"p256dh": "k", "auth": "s"},
                },
                headers=headers,
            )
            assert resp.status_code == 422

            # missing keys
            resp = await client.post(
                f"{API}/subscribe",
                json={"endpoint": _endpoint("nokeys")},
                headers=headers,
            )
            assert resp.status_code == 422

            # oversized endpoint
            resp = await client.post(
                f"{API}/subscribe",
                json={
                    "endpoint": "https://x.example/" + "a" * 2100,
                    "keys": {"p256dh": "k", "auth": "s"},
                },
                headers=headers,
            )
            assert resp.status_code == 422

            # no rows should have been created
            async with get_async_session() as db:
                assert await WebPushSubscription.list_for_user(db, user.id) == []
                await self._cleanup(db, [user])

        self.run(self._scenario_http(fn))

    def test_subscribe_unsubscribe_flow(self):
        async def fn(client):
            async with get_async_session() as db:
                user = await self._create_user(db)
            headers = self._auth(user)
            endpoint = _endpoint("flow")

            resp = await client.post(
                f"{API}/subscribe",
                json=_sub_payload(endpoint),
                headers=headers,
            )
            assert resp.status_code == 200
            assert resp.json()["data"]["endpoint"] == endpoint

            async with get_async_session() as db:
                rows = await WebPushSubscription.list_for_user(db, user.id)
                assert len(rows) == 1
                assert rows[0].endpoint == endpoint

            # idempotent re-subscribe with rotated keys -> single row, updated keys
            payload = _sub_payload(endpoint)
            payload["keys"]["p256dh"] = "rotated-key"
            resp = await client.post(f"{API}/subscribe", json=payload, headers=headers)
            assert resp.status_code == 200
            async with get_async_session() as db:
                rows = await WebPushSubscription.list_for_user(db, user.id)
                assert len(rows) == 1
                assert rows[0].p256dh == "rotated-key"

            # unsubscribe
            resp = await client.request(
                "DELETE",
                f"{API}/subscribe",
                json={"endpoint": endpoint},
                headers=headers,
            )
            assert resp.status_code == 200
            assert resp.json()["data"]["removed"] is True
            async with get_async_session() as db:
                assert await WebPushSubscription.list_for_user(db, user.id) == []

            # unsubscribe again -> removed False
            resp = await client.request(
                "DELETE",
                f"{API}/subscribe",
                json={"endpoint": endpoint},
                headers=headers,
            )
            assert resp.status_code == 200
            assert resp.json()["data"]["removed"] is False

            async with get_async_session() as db:
                await self._cleanup(db, [user])

        self.run(self._scenario_http(fn))

    def test_cross_user_hijack_rejected_and_per_user_cap(self):
        async def fn(client):
            async with get_async_session() as db:
                user_a = await self._create_user(db)
                user_b = await self._create_user(db)
            headers_a = self._auth(user_a)
            headers_b = self._auth(user_b)
            endpoint = _endpoint("hijack")

            resp = await client.post(
                f"{API}/subscribe", json=_sub_payload(endpoint), headers=headers_a
            )
            assert resp.status_code == 200

            # user B tries to claim user A's endpoint -> 400
            resp = await client.post(
                f"{API}/subscribe", json=_sub_payload(endpoint), headers=headers_b
            )
            assert resp.status_code == 400
            assert "another user" in resp.json()["detail"]["message"]

            # user B cannot unsubscribe user A's endpoint -> removed False
            resp = await client.request(
                "DELETE",
                f"{API}/subscribe",
                json={"endpoint": endpoint},
                headers=headers_b,
            )
            assert resp.status_code == 200
            assert resp.json()["data"]["removed"] is False
            async with get_async_session() as db:
                assert len(await WebPushSubscription.list_for_user(db, user_a.id)) == 1

            # per-user cap: A has 1; 9 more fit; the 11th is rejected
            for i in range(9):
                resp = await client.post(
                    f"{API}/subscribe",
                    json=_sub_payload(_endpoint(f"cap{i}")),
                    headers=headers_a,
                )
                assert resp.status_code == 200, resp.text
            resp = await client.post(
                f"{API}/subscribe",
                json=_sub_payload(_endpoint("cap-overflow")),
                headers=headers_a,
            )
            assert resp.status_code == 400
            assert "limit" in resp.json()["detail"]["message"].lower()

            async with get_async_session() as db:
                await self._cleanup(db, [user_a, user_b])

        self.run(self._scenario_http(fn))

    def test_test_push_endpoint(self):
        async def fn(client):
            async with get_async_session() as db:
                user = await self._create_user(db)
            headers = self._auth(user)

            # no subscription -> 400
            resp = await client.post(f"{API}/test", headers=headers)
            assert resp.status_code == 400

            endpoint = _endpoint("testpush")
            resp = await client.post(
                f"{API}/subscribe", json=_sub_payload(endpoint), headers=headers
            )
            assert resp.status_code == 200

            # delivered outcome (only the network hop is mocked)
            with patch(
                "app.api.v1.push.send_web_push",
                return_value=DeliveryOutcome(delivered=True),
            ) as send:
                resp = await client.post(f"{API}/test", headers=headers)
            assert resp.status_code == 200
            assert resp.json()["data"]["results"][0]["delivered"] is True
            send.assert_called_once()

            # expired outcome -> subscription pruned
            with patch(
                "app.api.v1.push.send_web_push",
                return_value=DeliveryOutcome(expired=True, error="410 gone"),
            ):
                resp = await client.post(f"{API}/test", headers=headers)
            assert resp.status_code == 200
            assert resp.json()["data"]["results"][0]["delivered"] is False
            async with get_async_session() as db:
                assert await WebPushSubscription.list_for_user(db, user.id) == []

            # blocked in production
            with patch.object(settings, "FASTAPI_ENV", "production"):
                resp = await client.post(f"{API}/test", headers=headers)
            assert resp.status_code == 400
            assert "production" in resp.json()["detail"]["message"].lower()

            async with get_async_session() as db:
                await self._cleanup(db, [user])

        self.run(self._scenario_http(fn))

    def test_rate_limiting_on_test_push(self):
        async def fn(client):
            # /push/test IP limit is 5 per 60s; 6th unauth request -> 429
            codes = []
            for _ in range(6):
                resp = await client.post(f"{API}/test")
                codes.append(resp.status_code)
            assert codes == [401, 401, 401, 401, 401, 429], codes

        self.run(self._scenario_http(fn))


class TestPushQueueE2E(E2EBase):
    def test_producer_consumer_full_cycle(self):
        # Imported locally: this module's import order must not touch
        # app.matching_ground.model before app.models is fully loaded.
        from app.worker.event_system import (
            EventNames,
            PushNotificationEvent,
            dispatch_event,
        )

        async def fn():
            redis = await get_redis_client()
            async with get_async_session() as db:
                user = await self._create_user(db)
                await WebPushSubscription.upsert(
                    db,
                    user_id=user.id,
                    endpoint=_endpoint("delivered"),
                    p256dh="k",
                    auth="s",
                )

            # REAL producer path: dispatch_event -> Notification row + queue + stream
            async with get_async_session() as db:
                await dispatch_event(
                    EventNames.PUSH_NOTIFICATION,
                    PushNotificationEvent(
                        user_id=str(user.id),
                        title="Hello",
                        body="World",
                        data={"type": "order.confirmed"},
                    ),
                    db=db,
                    redis=redis,
                )

            assert await redis.llen(PUSH_QUEUE_KEY) == 1
            async with get_async_session() as db:
                rows = (
                    (
                        await db.execute(
                            text(
                                "SELECT title, event_type, payload FROM notifications "
                                "WHERE user_id = :uid"
                            ),
                            {"uid": user.id},
                        )
                    )
                    .mappings()
                    .all()
                )
                assert len(rows) == 1
                assert rows[0]["title"] == "Hello"
                assert rows[0]["event_type"] == "push_notification"
                assert rows[0]["payload"] == {"type": "order.confirmed"}

            # REAL consumer (only the push-service hop mocked)
            with patch(
                "app.worker.tasks.web_push.send_web_push",
                return_value=DeliveryOutcome(delivered=True),
            ):
                processed = await _drain_once()
            assert processed == 1
            assert await redis.llen(PUSH_QUEUE_KEY) == 0
            assert await redis.llen(DLQ_KEY) == 0

            async with get_async_session() as db:
                assert len(await WebPushSubscription.list_for_user(db, user.id)) == 1
                await self._cleanup(db, [user])

        self.run(self._scenario_db(fn))

    def test_consumer_outcome_branches(self):
        async def fn():
            redis = await get_redis_client()
            async with get_async_session() as db:
                u_delivered = await self._create_user(db)
                u_past = await self._create_user(db)
                u_retry = await self._create_user(db)
                u_gone = await self._create_user(db)
                u_badkey = await self._create_user(db)
                await WebPushSubscription.upsert(
                    db,
                    user_id=u_delivered.id,
                    endpoint=_endpoint("delivered"),
                    p256dh="k",
                    auth="s",
                )
                await WebPushSubscription.upsert(
                    db,
                    user_id=u_past.id,
                    endpoint=_endpoint("past"),
                    p256dh="k",
                    auth="s",
                    expiration_time=datetime.now(UTC) - timedelta(hours=1),
                )
                await WebPushSubscription.upsert(
                    db,
                    user_id=u_retry.id,
                    endpoint=_endpoint("retry"),
                    p256dh="k",
                    auth="s",
                )
                await WebPushSubscription.upsert(
                    db,
                    user_id=u_gone.id,
                    endpoint=_endpoint("gone"),
                    p256dh="k",
                    auth="s",
                )
                await WebPushSubscription.upsert(
                    db,
                    user_id=u_badkey.id,
                    endpoint=_endpoint("badkey"),
                    p256dh="k",
                    auth="s",
                )

            for u in (u_delivered, u_past, u_retry, u_gone, u_badkey):
                await redis.rpush(
                    PUSH_QUEUE_KEY,
                    json.dumps(
                        {"user_id": str(u.id), "title": "T", "body": "B", "data": {}}
                    ),
                )
            await redis.rpush(PUSH_QUEUE_KEY, "not-json{")
            await redis.rpush(
                PUSH_QUEUE_KEY,
                json.dumps(
                    {"user_id": "not-a-uuid", "title": "T", "body": "B", "data": {}}
                ),
            )

            def send_side_effect(sub, **kwargs):
                by_endpoint = {
                    "delivered": DeliveryOutcome(delivered=True),
                    "retry": DeliveryOutcome(retry=True, error="429"),
                    "gone": DeliveryOutcome(expired=True, error="410"),
                    "badkey": DeliveryOutcome(error="invalid key"),
                }
                return by_endpoint[sub.endpoint.rsplit("-", 1)[-1]]

            with patch(
                "app.worker.tasks.web_push.send_web_push",
                side_effect=send_side_effect,
            ):
                processed = await _drain_once()

            assert processed == 7  # 5 valid payloads + malformed + bad uuid
            # the retry payload was requeued once at the tail
            remaining = await redis.lrange(PUSH_QUEUE_KEY, 0, -1)
            assert len(remaining) == 1
            assert json.loads(remaining[0])["user_id"] == str(u_retry.id)
            # permanent failure went to the DLQ
            dlq_items = await redis.lrange(DLQ_KEY, 0, -1)
            assert len(dlq_items) == 1
            assert json.loads(dlq_items[0])["user_id"] == str(u_badkey.id)

            async with get_async_session() as db:
                assert (
                    len(await WebPushSubscription.list_for_user(db, u_delivered.id))
                    == 1
                )
                # browser-declared expiration in the past -> pruned without sending
                assert await WebPushSubscription.list_for_user(db, u_past.id) == []
                # 410 from push service -> removed
                assert await WebPushSubscription.list_for_user(db, u_gone.id) == []
                # transient failure -> subscription kept
                assert len(await WebPushSubscription.list_for_user(db, u_retry.id)) == 1
                # permanent failure -> subscription kept, payload on DLQ
                assert (
                    len(await WebPushSubscription.list_for_user(db, u_badkey.id)) == 1
                )
                await self._cleanup(
                    db, [u_delivered, u_past, u_retry, u_gone, u_badkey]
                )

        self.run(self._scenario_db(fn))

    def test_chat_events_not_duplicated_to_notifications_table(self):
        from app.worker.event_system import (
            EventNames,
            PushNotificationEvent,
            dispatch_event,
        )

        async def fn():
            redis = await get_redis_client()
            async with get_async_session() as db:
                user = await self._create_user(db)
            async with get_async_session() as db:
                await dispatch_event(
                    EventNames.PUSH_NOTIFICATION,
                    PushNotificationEvent(
                        user_id=str(user.id),
                        title="chat",
                        body="message",
                        data={"type": "chat.dm"},
                    ),
                    db=db,
                    redis=redis,
                )
            assert await redis.llen(PUSH_QUEUE_KEY) == 1
            async with get_async_session() as db:
                rows = (
                    await db.execute(
                        text("SELECT id FROM notifications WHERE user_id = :uid"),
                        {"uid": user.id},
                    )
                ).all()
                assert rows == []
                await self._cleanup(db, [user])

        self.run(self._scenario_db(fn))

    def test_model_crud_and_ownership(self):
        async def fn():
            async with get_async_session() as db:
                user_a = await self._create_user(db)
                user_b = await self._create_user(db)
                endpoint = _endpoint("crud")

                # upsert creates
                first = await WebPushSubscription.upsert(
                    db, user_id=user_a.id, endpoint=endpoint, p256dh="k1", auth="s1"
                )
                assert first.id is not None

                # upsert updates in place (same endpoint -> single row)
                second = await WebPushSubscription.upsert(
                    db, user_id=user_a.id, endpoint=endpoint, p256dh="k2", auth="s2"
                )
                assert second.id == first.id
                assert second.p256dh == "k2"

                rows = await WebPushSubscription.list_for_user(db, user_a.id)
                assert len(rows) == 1

                # ownership: user B cannot delete A's subscription
                assert (
                    await WebPushSubscription.delete_by_endpoint(
                        db, user_id=user_b.id, endpoint=endpoint
                    )
                    is False
                )
                assert len(await WebPushSubscription.list_for_user(db, user_a.id)) == 1

                # owner can delete
                assert (
                    await WebPushSubscription.delete_by_endpoint(
                        db, user_id=user_a.id, endpoint=endpoint
                    )
                    is True
                )
                assert await WebPushSubscription.list_for_user(db, user_a.id) == []

                # deleting an unknown endpoint -> False
                assert (
                    await WebPushSubscription.delete_by_endpoint(
                        db, user_id=user_a.id, endpoint=_endpoint("nope")
                    )
                    is False
                )

                await self._cleanup(db, [user_a, user_b])

        self.run(self._scenario_db(fn))
