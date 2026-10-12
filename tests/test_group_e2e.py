"""End-to-end tests for the group chat feature.

These run against the REAL FastAPI app, REAL Postgres and REAL Redis. Users are
seeded directly in the database and authenticated with real JWTs (the same
approach used by ``test_web_push_e2e.py``). All test-created state (users,
groups, memberships, messages) is cleaned up afterwards.
"""

from __future__ import annotations

import asyncio
import contextlib
import json
from uuid import uuid4

import httpx
from httpx import ASGITransport
from sqlalchemy import text
from starlette.datastructures import QueryParams
from starlette.websockets import WebSocketDisconnect

from app.core.security import create_token
from app.db.postgres_db_conn import engine, get_async_session
from app.db.redis import close_redis_client, get_redis_client
from app.models.user import User
from app.service.group_service import group_service
from app.service.group_ws_service import (
    deliver_group_payload,
    group_pubsub_dispatcher,
    handle_group_websocket,
)
from main import app

API = "/api/v1/groups"
BASE_URL = "http://testserver"


class GroupE2EBase:
    def run(self, coro):
        return asyncio.run(coro)

    async def _create_user(self, db) -> User:
        # ``is_store_owner`` is passed explicitly because the dev DB column has
        # no server default (the model declares one); auth_service does the same.
        return await User.create(
            {
                "email": f"e2e_group_{uuid4().hex[:12]}@bouwnce.test",
                "full_name": "E2E Group Tester",
                "role": "user",
                "is_store_owner": False,
            },
            db,
        )

    @staticmethod
    def _auth(user: User) -> dict[str, str]:
        return {"Authorization": f"Bearer {create_token(str(user.id))}"}

    async def _cleanup(self, db, users: list[User], group_ids: list[str]) -> None:
        for group_id in group_ids:
            await db.execute(
                text("DELETE FROM group_messages WHERE group_id = :gid"),
                {"gid": group_id},
            )
            await db.execute(
                text("DELETE FROM group_members WHERE group_id = :gid"),
                {"gid": group_id},
            )
            await db.execute(
                text("DELETE FROM groups WHERE id = :gid"), {"gid": group_id}
            )
        for user in users:
            await db.execute(
                text("DELETE FROM group_members WHERE user_id = :uid"),
                {"uid": user.id},
            )
            await db.execute(
                text("DELETE FROM users WHERE id = :uid"), {"uid": user.id}
            )
        await db.flush()

    async def _scenario(self, fn):
        """Run the real ASGI app against real Postgres/Redis in one loop."""
        try:
            async with httpx.AsyncClient(
                transport=ASGITransport(app=app), base_url=BASE_URL
            ) as client:
                await fn(client)
        finally:
            await close_redis_client()
            await engine.dispose()

    async def _scenario_db(self, fn):
        """Run a DB-only scenario (no HTTP) in one event loop."""
        try:
            await fn()
        finally:
            # The group dispatcher is a module singleton whose background task is
            # bound to this loop; stop it before the loop is torn down so the
            # next test can start it cleanly.
            with contextlib.suppress(Exception):
                await group_pubsub_dispatcher.stop()
            await close_redis_client()
            await engine.dispose()

    @staticmethod
    async def _wait_until(predicate, timeout: float = 5.0):
        loop = asyncio.get_running_loop()
        deadline = loop.time() + timeout
        while loop.time() < deadline:
            if predicate():
                return
            await asyncio.sleep(0.02)
        raise AssertionError("condition was not met in time")


class TestGroupApiE2E(GroupE2EBase):
    def test_group_lifecycle(self):
        async def fn(client):
            group_ids: list[str] = []
            async with get_async_session() as db:
                owner = await self._create_user(db)
                member = await self._create_user(db)
                outsider = await self._create_user(db)
            owner_h = self._auth(owner)
            member_h = self._auth(member)
            outsider_h = self._auth(outsider)
            name = f"grp-{uuid4().hex[:10]}"

            try:
                # ----- create -----
                resp = await client.post(
                    API,
                    json={"name": name, "description": "e2e group"},
                    headers=owner_h,
                )
                assert resp.status_code == 201, resp.text
                group = resp.json()
                group_ids.append(group["id"])
                assert group["name"] == name
                assert group["member_count"] == 1
                assert group["is_owner"] is True
                assert group["created_by"] == str(owner.id)

                # ----- list (owner) -----
                resp = await client.get(API, headers=owner_h)
                assert resp.status_code == 200, resp.text
                listed = resp.json()
                assert any(g["id"] == group["id"] for g in listed)

                # ----- get details -----
                resp = await client.get(f"{API}/{group['id']}", headers=owner_h)
                assert resp.status_code == 200, resp.text
                assert resp.json()["id"] == group["id"]

                # ----- non-member access is forbidden -----
                resp = await client.get(f"{API}/{group['id']}", headers=outsider_h)
                assert resp.status_code == 403, resp.text

                # ----- update (owner) -----
                resp = await client.patch(
                    f"{API}/{group['id']}",
                    json={"description": "updated description"},
                    headers=owner_h,
                )
                assert resp.status_code == 200, resp.text
                assert resp.json()["description"] == "updated description"

                # ----- add member (owner) -----
                resp = await client.post(
                    f"{API}/{group['id']}/members",
                    json={"user_id": str(member.id)},
                    headers=owner_h,
                )
                assert resp.status_code == 201, resp.text
                assert resp.json()["role"] == "member"
                assert resp.json()["user_id"] == str(member.id)

                # ----- duplicate add conflicts -----
                resp = await client.post(
                    f"{API}/{group['id']}/members",
                    json={"user_id": str(member.id)},
                    headers=owner_h,
                )
                assert resp.status_code == 409, resp.text

                # ----- add by a non-admin is forbidden -----
                resp = await client.post(
                    f"{API}/{group['id']}/members",
                    json={"user_id": str(outsider.id)},
                    headers=member_h,
                )
                assert resp.status_code == 403, resp.text

                # ----- list members -----
                resp = await client.get(
                    f"{API}/{group['id']}/members", headers=member_h
                )
                assert resp.status_code == 200, resp.text
                member_ids = {m["user_id"] for m in resp.json()}
                assert str(owner.id) in member_ids
                assert str(member.id) in member_ids

                # ----- send message (member) -----
                resp = await client.post(
                    f"{API}/{group['id']}/messages",
                    json={"body": "hello group"},
                    headers=member_h,
                )
                assert resp.status_code == 201, resp.text
                message = resp.json()
                assert message["body"] == "hello group"
                assert message["sender_id"] == str(member.id)

                # ----- non-member cannot send -----
                resp = await client.post(
                    f"{API}/{group['id']}/messages",
                    json={"body": "intruder"},
                    headers=outsider_h,
                )
                assert resp.status_code == 403, resp.text

                # ----- list messages -----
                resp = await client.get(
                    f"{API}/{group['id']}/messages", headers=owner_h
                )
                assert resp.status_code == 200, resp.text
                assert len(resp.json()) == 1

                # ----- edit own message -----
                resp = await client.patch(
                    f"{API}/{group['id']}/messages/{message['id']}",
                    json={"body": "hello group (edited)"},
                    headers=member_h,
                )
                assert resp.status_code == 200, resp.text
                assert resp.json()["is_edited"] is True
                assert resp.json()["body"] == "hello group (edited)"

                # ----- cannot edit someone else's message -----
                resp = await client.patch(
                    f"{API}/{group['id']}/messages/{message['id']}",
                    json={"body": "hijacked"},
                    headers=owner_h,
                )
                assert resp.status_code == 403, resp.text

                # ----- mentions: mention a real member -----
                resp = await client.post(
                    f"{API}/{group['id']}/messages",
                    json={
                        "body": "hey @member",
                        "mentioned_user_ids": [str(member.id)],
                    },
                    headers=owner_h,
                )
                assert resp.status_code == 201, resp.text

                resp = await client.get(
                    f"{API}/{group['id']}/mentioned", headers=member_h
                )
                assert resp.status_code == 200, resp.text
                assert any(m["body"] == "hey @member" for m in resp.json()), resp.text

                # ----- mention a non-member is rejected -----
                resp = await client.post(
                    f"{API}/{group['id']}/messages",
                    json={
                        "body": "hey @outsider",
                        "mentioned_user_ids": [str(outsider.id)],
                    },
                    headers=owner_h,
                )
                assert resp.status_code == 400, resp.text

                # ----- invite link (owner) -----
                resp = await client.post(f"{API}/{group['id']}/invite", headers=owner_h)
                assert resp.status_code == 200, resp.text
                assert resp.json()["group_id"] == group["id"]

                # ----- invite link by a regular member is forbidden -----
                resp = await client.post(
                    f"{API}/{group['id']}/invite", headers=member_h
                )
                assert resp.status_code == 403, resp.text

                # ----- stats -----
                resp = await client.get(f"{API}/{group['id']}/stats", headers=member_h)
                assert resp.status_code == 200, resp.text
                stats = resp.json()
                assert stats["member_count"] == 2
                assert stats["active_member_count"] == 2
                assert stats["owner_count"] == 1
                assert stats["message_count"] == 2

                # ----- transfer ownership -----
                resp = await client.post(
                    f"{API}/{group['id']}/transfer-ownership",
                    params={"new_owner_id": str(member.id)},
                    headers=owner_h,
                )
                assert resp.status_code == 200, resp.text
                members = (
                    await client.get(f"{API}/{group['id']}/members", headers=member_h)
                ).json()
                roles = {m["user_id"]: m["role"] for m in members}
                assert roles[str(member.id)] == "owner"
                assert roles[str(owner.id)] == "admin"

                # ----- delete own message -----
                resp = await client.delete(
                    f"{API}/{group['id']}/messages/{message['id']}",
                    headers=member_h,
                )
                assert resp.status_code == 204, resp.text

                # ----- remove member (new owner) -----
                resp = await client.delete(
                    f"{API}/{group['id']}/members/{owner.id}",
                    headers=member_h,
                )
                assert resp.status_code == 204, resp.text
                members = (
                    await client.get(f"{API}/{group['id']}/members", headers=member_h)
                ).json()
                assert str(owner.id) not in {m["user_id"] for m in members}

                # ----- delete group (owner) -----
                resp = await client.delete(f"{API}/{group['id']}", headers=member_h)
                assert resp.status_code == 204, resp.text
                resp = await client.get(f"{API}/{group['id']}", headers=member_h)
                assert resp.status_code == 404, resp.text
            finally:
                async with get_async_session() as db:
                    await self._cleanup(db, [owner, member, outsider], group_ids)

        self.run(self._scenario(fn))

    def test_auth_is_required(self):
        async def fn(client):
            resp = await client.get(API)
            assert resp.status_code == 401  # HTTPBearer: missing credentials
            resp = await client.post(API, json={"name": "no-auth"})
            assert resp.status_code == 401

        self.run(self._scenario(fn))


class FakeWebSocket:
    """Minimal WebSocket stand-in for driving ``handle_group_websocket``."""

    def __init__(
        self,
        token: str,
        group_id: str,
        incoming: list[str] | None = None,
    ) -> None:
        self.query_params = QueryParams({"token": token, "group_id": group_id})
        self._incoming: asyncio.Queue = asyncio.Queue()
        for item in incoming or []:
            self._incoming.put_nowait(item)
        self.sent: list[dict | str] = []
        self.accepted = False
        self.closed = False

    async def accept(self) -> None:
        self.accepted = True

    async def receive_text(self) -> str:
        item = await self._incoming.get()
        if item == "__close__":
            raise WebSocketDisconnect(code=1000)
        return item

    async def send_text(self, payload: str) -> None:
        try:
            self.sent.append(json.loads(payload))
        except json.JSONDecodeError:
            self.sent.append(payload)

    async def send_json(self, payload: dict) -> None:
        self.sent.append(payload)

    async def close(self, code: int = 1000) -> None:
        self.closed = True
        self._incoming.put_nowait("__close__")

    def close_later(self) -> None:
        self._incoming.put_nowait("__close__")

    def feed(self, payload: dict) -> None:
        """Queue an inbound frame for the running handler to process."""
        self._incoming.put_nowait(json.dumps(payload))

    def messages(self, message_type: str) -> list[dict]:
        return [
            m
            for m in self.sent
            if isinstance(m, dict) and m.get("type") == message_type
        ]


class TestGroupWebSocketE2E(GroupE2EBase):
    def test_member_receives_broadcast_and_non_member_is_rejected(self):
        async def fn():
            group_ids: list[str] = []
            async with get_async_session() as db:
                owner = await self._create_user(db)
                member = await self._create_user(db)
                outsider = await self._create_user(db)

            try:
                async with get_async_session() as db:
                    created = await group_service.create_group(
                        db=db,
                        name=f"ws-{uuid4().hex[:10]}",
                        created_by=str(owner.id),
                    )
                    group_id = created["data"]["group"]["id"]
                    group_ids.append(group_id)
                async with get_async_session() as db:
                    await group_service.add_member(
                        db=db,
                        group_id=group_id,
                        user_id=str(member.id),
                        added_by=str(owner.id),
                    )

                owner_token = create_token(str(owner.id))
                member_token = create_token(str(member.id))
                outsider_token = create_token(str(outsider.id))

                # A non-member must be rejected (closed with code 1008).
                outsider_ws = FakeWebSocket(outsider_token, group_id)
                await handle_group_websocket(outsider_ws, outsider_token)
                assert outsider_ws.closed is True
                assert outsider_ws.accepted is False

                member_ws = FakeWebSocket(member_token, group_id)
                member_task = asyncio.create_task(
                    handle_group_websocket(member_ws, member_token)
                )
                await self._wait_until(lambda: member_ws.accepted)

                owner_ws = FakeWebSocket(
                    owner_token,
                    group_id,
                    incoming=[json.dumps({"type": "group_message", "body": "hi ws"})],
                )
                owner_task = asyncio.create_task(
                    handle_group_websocket(owner_ws, owner_token)
                )
                await self._wait_until(lambda: owner_ws.accepted)

                await self._wait_until(
                    lambda: bool(member_ws.messages("group_message"))
                )
                delivered = member_ws.messages("group_message")
                assert delivered[0]["data"]["body"] == "hi ws"
                assert delivered[0]["data"]["sender_id"] == str(owner.id)
                assert owner_ws.messages("group_message_sent")

                member_ws.close_later()
                owner_ws.close_later()
                with contextlib.suppress(Exception):
                    await member_task
                with contextlib.suppress(Exception):
                    await owner_task
            finally:
                async with get_async_session() as db:
                    await self._cleanup(db, [owner, member, outsider], group_ids)

        self.run(self._scenario_db(fn))


class TestGroupWebSocketParityE2E(GroupE2EBase):
    """WebSocket delivery paths that mirror the direct-message chat model.

    These exercise the Redis pub/sub fan-out (cross-worker delivery), the
    per-group stream catch-up on reconnect, and the push/mobile + notification
    side effects that offline members receive.
    """

    async def _setup_group(self, users: list[User]) -> str:
        """Create a group owned by ``users[0]`` with the rest as members."""
        async with get_async_session() as db:
            created = await group_service.create_group(
                db=db,
                name=f"parity-{uuid4().hex[:10]}",
                created_by=str(users[0].id),
            )
            group_id = created["data"]["group"]["id"]
        async with get_async_session() as db:
            for user in users[1:]:
                await group_service.add_member(
                    db=db,
                    group_id=group_id,
                    user_id=str(user.id),
                    added_by=str(users[0].id),
                )
        return group_id

    @staticmethod
    async def _cleanup_group_redis(redis, group_id, user_ids) -> None:
        keys = [f"group:events:stream:{group_id}"]
        keys += [f"group:events:last:{group_id}:{uid}" for uid in user_ids]
        with contextlib.suppress(Exception):
            await redis.delete(*keys)

    @staticmethod
    async def _wait_for_push(redis, queue_key: str, user_id: str, timeout: float = 5.0):
        loop = asyncio.get_running_loop()
        deadline = loop.time() + timeout
        while loop.time() < deadline:
            for raw in await redis.lrange(queue_key, 0, -1):
                try:
                    item = json.loads(raw)
                except (TypeError, json.JSONDecodeError):
                    continue
                if str(item.get("user_id")) == str(user_id):
                    return item
            await asyncio.sleep(0.02)
        raise AssertionError("push notification was not enqueued in time")

    def test_cross_worker_pubsub_fanout_and_typing(self):
        """A socket that is not in this worker's manager still gets frames."""

        async def fn():
            group_ids: list[str] = []
            redis = await get_redis_client()
            async with get_async_session() as db:
                owner = await self._create_user(db)
                member = await self._create_user(db)
            owner_task = None
            try:
                group_id = await self._setup_group([owner, member])
                group_ids.append(group_id)
                owner_token = create_token(str(owner.id))
                member_token = create_token(str(member.id))

                # Worker A: only the owner has a local socket.
                owner_ws = FakeWebSocket(owner_token, group_id)
                owner_task = asyncio.create_task(
                    handle_group_websocket(owner_ws, owner_token)
                )
                await self._wait_until(lambda: owner_ws.accepted)
                await self._wait_until(lambda: bool(owner_ws.messages("group.ready")))

                # Worker B: register a member socket directly with the shared
                # dispatcher. It is NOT in this worker's connection manager, so
                # the only way it can receive anything is the Redis pub/sub path.
                await group_pubsub_dispatcher.start(redis)
                remote_ws = FakeWebSocket(member_token, group_id)
                await group_pubsub_dispatcher.register(
                    user_id=str(member.id),
                    connection_id="remote-worker",
                    send_callback=lambda payload, _lock: deliver_group_payload(
                        redis=redis,
                        websocket=remote_ws,
                        payload=payload,
                        user_id=str(member.id),
                        send_lock=None,
                    ),
                )

                owner_ws.feed({"type": "group_message", "body": "from worker A"})
                await self._wait_until(
                    lambda: bool(remote_ws.messages("group_message"))
                )
                delivered = remote_ws.messages("group_message")[-1]
                assert delivered["data"]["body"] == "from worker A"
                assert delivered["data"]["sender_id"] == str(owner.id)

                # Typing is pub/sub-only and must never echo back to the sender.
                owner_ws.feed({"type": "group_typing", "is_typing": True})
                await self._wait_until(lambda: bool(remote_ws.messages("group_typing")))
                typing = remote_ws.messages("group_typing")[-1]
                assert typing["data"]["user_id"] == str(owner.id)
                assert typing["data"]["is_typing"] is True
                assert not owner_ws.messages("group_typing")
            finally:
                with contextlib.suppress(Exception):
                    await group_pubsub_dispatcher.unregister(
                        user_id=str(member.id), connection_id="remote-worker"
                    )
                if owner_task is not None:
                    with contextlib.suppress(Exception):
                        owner_ws.close_later()
                        await owner_task
                with contextlib.suppress(Exception):
                    from app.worker.tasks.web_push import PUSH_QUEUE_KEY

                    await redis.delete(PUSH_QUEUE_KEY)
                await self._cleanup_group_redis(
                    redis, group_id if group_ids else "", [owner.id, member.id]
                )
                async with get_async_session() as db:
                    await self._cleanup(db, [owner, member], group_ids)

        self.run(self._scenario_db(fn))

    def test_offline_member_receives_push_and_notification(self):
        """A member with no socket still gets a push event and a notification."""
        from app.worker.tasks.web_push import PUSH_QUEUE_KEY

        async def fn():
            group_ids: list[str] = []
            redis = await get_redis_client()
            await redis.delete(PUSH_QUEUE_KEY)
            async with get_async_session() as db:
                owner = await self._create_user(db)
                member = await self._create_user(db)
            owner_task = None
            try:
                group_id = await self._setup_group([owner, member])
                group_ids.append(group_id)
                owner_token = create_token(str(owner.id))

                # The member never opens a socket: it must still be notified.
                owner_ws = FakeWebSocket(
                    owner_token,
                    group_id,
                    incoming=[
                        json.dumps({"type": "group_message", "body": "ping offline"})
                    ],
                )
                owner_task = asyncio.create_task(
                    handle_group_websocket(owner_ws, owner_token)
                )
                await self._wait_until(lambda: owner_ws.accepted)

                payload = await self._wait_for_push(
                    redis, PUSH_QUEUE_KEY, str(member.id)
                )
                assert payload["title"]
                assert payload["data"]["type"] == "group.message.created"
                assert payload["data"]["group_id"] == group_id
                assert payload["data"]["sender_id"] == str(owner.id)

                async with get_async_session() as db:
                    rows = (
                        (
                            await db.execute(
                                text(
                                    "SELECT event_type, payload FROM notifications "
                                    "WHERE user_id = :uid"
                                ),
                                {"uid": member.id},
                            )
                        )
                        .mappings()
                        .all()
                    )
                assert len(rows) == 1
                assert rows[0]["event_type"] == "group_message"
                assert rows[0]["payload"]["group_id"] == group_id
            finally:
                if owner_task is not None:
                    with contextlib.suppress(Exception):
                        owner_ws.close_later()
                        await owner_task
                with contextlib.suppress(Exception):
                    await redis.delete(PUSH_QUEUE_KEY)
                await self._cleanup_group_redis(
                    redis, group_ids[0] if group_ids else "", [owner.id, member.id]
                )
                async with get_async_session() as db:
                    await self._cleanup(db, [owner, member], group_ids)

        self.run(self._scenario_db(fn))

    def test_reconnect_replays_missed_message_from_stream(self):
        """A member that reconnects catches up on messages sent while away."""
        from app.worker.tasks.web_push import PUSH_QUEUE_KEY

        async def fn():
            group_ids: list[str] = []
            redis = await get_redis_client()
            await redis.delete(PUSH_QUEUE_KEY)
            async with get_async_session() as db:
                owner = await self._create_user(db)
                member = await self._create_user(db)
            owner_ws = member_ws = None
            owner_task = member_task = None
            try:
                group_id = await self._setup_group([owner, member])
                group_ids.append(group_id)
                owner_token = create_token(str(owner.id))
                member_token = create_token(str(member.id))

                # The member connects once (this anchors its stream cursor)
                # and then drops before any message is sent.
                first_member_ws = FakeWebSocket(member_token, group_id)
                first_task = asyncio.create_task(
                    handle_group_websocket(first_member_ws, member_token)
                )
                await self._wait_until(lambda: first_member_ws.accepted)
                await self._wait_until(
                    lambda: bool(first_member_ws.messages("group.ready"))
                )
                first_member_ws.close_later()
                await first_task

                # The owner sends while the member is offline.
                owner_ws = FakeWebSocket(
                    owner_token,
                    group_id,
                    incoming=[
                        json.dumps({"type": "group_message", "body": "missed you"})
                    ],
                )
                owner_task = asyncio.create_task(
                    handle_group_websocket(owner_ws, owner_token)
                )
                await self._wait_until(lambda: owner_ws.accepted)
                await self._wait_until(
                    lambda: bool(owner_ws.messages("group_message_sent"))
                )

                # On reconnect the missed message must be replayed from the
                # per-group Redis stream.
                member_ws = FakeWebSocket(member_token, group_id)
                member_task = asyncio.create_task(
                    handle_group_websocket(member_ws, member_token)
                )
                await self._wait_until(lambda: member_ws.accepted)
                await self._wait_until(
                    lambda: bool(member_ws.messages("group_message"))
                )
                caught_up = member_ws.messages("group_message")[-1]
                assert caught_up["data"]["body"] == "missed you"
            finally:
                for websocket, task in (
                    (member_ws, member_task),
                    (owner_ws, owner_task),
                ):
                    if task is not None and websocket is not None:
                        websocket.close_later()
                        with contextlib.suppress(Exception):
                            await task
                with contextlib.suppress(Exception):
                    await redis.delete(PUSH_QUEUE_KEY)
                await self._cleanup_group_redis(
                    redis, group_ids[0] if group_ids else "", [owner.id, member.id]
                )
                async with get_async_session() as db:
                    await self._cleanup(db, [owner, member], group_ids)

        self.run(self._scenario_db(fn))
