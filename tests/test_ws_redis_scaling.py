"""Tests for the Phase 1 Redis connection scaling refactoring.

Covers:
- PubSubDispatcher: single psubscribe, dispatch to correct user, unregister
- _catchup_chat_stream: one-time non-blocking XREAD, no persistent connection
"""

from __future__ import annotations

import asyncio
import json
from contextlib import asynccontextmanager
from types import SimpleNamespace
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest

from app.service import group_ws_service, mobile_events_service
from app.service.ws_chat import ChatDelivery
from app.service.ws_presence import PresenceManager, PubSubDispatcher, pubsub_dispatcher


class TestPubSubDispatcher:
    """Verify the shared pubsub dispatcher routes messages correctly."""

    @pytest.fixture
    def mock_redis(self):
        """A mock Redis client with a mock pubsub.

        Real redis-py: redis.pubsub() returns a PubSub instance.
        PubSub.psubscribe() is a coroutine method.
        """
        redis = AsyncMock()
        pubsub = AsyncMock()
        redis.pubsub.return_value = pubsub

        pubsub.psubscribe = AsyncMock()
        pubsub.aclose = AsyncMock()
        pubsub.listen.return_value = iter([])
        return redis, pubsub

    @pytest.mark.asyncio
    async def test_start_creates_psubscribe(self, mock_redis):
        redis, pubsub = mock_redis
        dispatcher = PubSubDispatcher()
        await dispatcher.start(redis)
        try:
            redis.pubsub.assert_called_once()
            pubsub.psubscribe.assert_awaited_once_with("chat:user:*", "group:user:*")
            assert dispatcher._pubsub is pubsub
            assert dispatcher._task is not None
        finally:
            await dispatcher.stop()

    @pytest.mark.asyncio
    async def test_start_is_idempotent(self, mock_redis):
        redis, pubsub = mock_redis
        dispatcher = PubSubDispatcher()
        await dispatcher.start(redis)
        await dispatcher.start(redis)  # second call should be no-op
        try:
            assert redis.pubsub.call_count == 1
        finally:
            await dispatcher.stop()

    @pytest.mark.asyncio
    async def test_stop_cancels_task_and_closes_pubsub(self, mock_redis):
        redis, pubsub = mock_redis
        dispatcher = PubSubDispatcher()
        await dispatcher.start(redis)
        assert dispatcher._task is not None
        assert not dispatcher._task.done()
        await dispatcher.stop()
        assert dispatcher._task is None
        assert dispatcher._pubsub is None
        pubsub.aclose.assert_called_once()

    @pytest.mark.asyncio
    async def test_register_and_unregister(self, mock_redis):
        redis, pubsub = mock_redis
        dispatcher = PubSubDispatcher()
        await dispatcher.start(redis)

        callback_mock = AsyncMock()
        callback_mock.return_value = asyncio.ensure_future(asyncio.sleep(0))
        await dispatcher.register(user_id="user-1", send_callback=callback_mock)
        assert "user-1" in dispatcher._callbacks

        await dispatcher.unregister(user_id="user-1")
        assert "user-1" not in dispatcher._callbacks

        await dispatcher.stop()

    @pytest.mark.asyncio
    async def test_dispatch_routes_to_correct_user(self, mock_redis):
        """The dispatcher must deliver a message published to
        chat:user:alice only to alice's callback, not to bob's."""
        redis, pubsub = mock_redis
        listen_future = asyncio.Future()
        pubsub.listen.return_value = listen_future

        dispatcher = PubSubDispatcher()
        await dispatcher.start(redis)

        alice_callback = AsyncMock()
        bob_callback = AsyncMock()
        await dispatcher.register(user_id="alice", send_callback=alice_callback)
        await dispatcher.register(user_id="bob", send_callback=bob_callback)

        msg = {
            "type": "pmessage",
            "channel": b"chat:user:alice",
            "data": json.dumps(
                {"type": "chat.message", "data": {"id": "123"}}
            ).encode(),
        }
        listen_future.set_result(iter([msg, None]))

        await asyncio.sleep(0.1)

        alice_callback.assert_called_once()
        bob_callback.assert_not_called()

        await dispatcher.stop()

    @pytest.mark.asyncio
    async def test_dispatch_skips_originating_socket_for_sender_echo(self):
        dispatcher = PubSubDispatcher()
        originating_socket = AsyncMock()
        sender_other_device = AsyncMock()
        await dispatcher.register(
            user_id="alice",
            connection_id="originating-socket",
            send_callback=originating_socket,
        )
        await dispatcher.register(
            user_id="alice",
            connection_id="other-device",
            send_callback=sender_other_device,
        )
        frame = {"type": "chat.message", "data": {"id": "message-1"}}

        await dispatcher._dispatch_message(
            {
                "type": "pmessage",
                "channel": b"chat:user:alice",
                "data": json.dumps(
                    {**frame, "_exclude_connection_id": "originating-socket"}
                ).encode(),
            }
        )
        await asyncio.sleep(0.1)

        originating_socket.assert_not_awaited()
        sender_other_device.assert_awaited_once_with(frame, None)

    @pytest.mark.asyncio
    async def test_fanout_marks_only_sender_channel_for_socket_exclusion(self):
        class Pipeline:
            def __init__(self):
                self.published = []
                self.streamed = []

            async def __aenter__(self):
                return self

            async def __aexit__(self, *_):
                return None

            def publish(self, channel, payload):
                self.published.append((channel, json.loads(payload)))

            def xadd(self, key, fields, **kwargs):
                self.streamed.append((key, fields))

            async def execute(self):
                return None

        class Redis:
            def __init__(self):
                self.pipe = Pipeline()

            def pipeline(self):
                return self.pipe

        redis = Redis()
        event = {
            "type": "chat.message",
            "data": {
                "id": "message-1",
                "sender_id": "alice",
                "recipient_id": "bob",
            },
        }
        payload = SimpleNamespace(
            model_dump_json=lambda: json.dumps(event),
            model_dump=lambda **_: json.loads(json.dumps(event)),
        )

        await ChatDelivery()._publish_chat_message_fanout(
            redis=redis,
            sender_id="alice",
            sender_connection_id="originating-socket",
            recipient_id="bob",
            conversation_id="conversation-1",
            payload=payload,
        )

        published = dict(redis.pipe.published)
        assert published["chat:user:alice"] == {
            **event,
            "_exclude_connection_id": "originating-socket",
        }
        assert published["chat:user:bob"] == event
        assert published["chat:conversation:conversation-1"] == event
        assert json.loads(redis.pipe.streamed[0][1]["data"]) == event

    @pytest.mark.asyncio
    async def test_dispatch_delivers_to_all_of_a_users_connections(self, mock_redis):
        redis, pubsub = mock_redis
        listen_future = asyncio.Future()
        pubsub.listen.return_value = listen_future
        dispatcher = PubSubDispatcher()
        await dispatcher.start(redis)

        first_device = AsyncMock()
        second_device = AsyncMock()
        await dispatcher.register(
            user_id="alice", connection_id="phone", send_callback=first_device
        )
        await dispatcher.register(
            user_id="alice", connection_id="browser", send_callback=second_device
        )
        listen_future.set_result(
            iter(
                [
                    {
                        "type": "pmessage",
                        "channel": b"chat:user:alice",
                        "data": json.dumps({"type": "chat.message"}).encode(),
                    },
                    None,
                ]
            )
        )

        await asyncio.sleep(0.1)

        first_device.assert_called_once()
        second_device.assert_called_once()
        await dispatcher.stop()

    @pytest.mark.asyncio
    async def test_dispatch_scopes_callbacks_to_channel_prefix(self, mock_redis):
        redis, pubsub = mock_redis
        listen_future = asyncio.Future()
        pubsub.listen.return_value = listen_future
        dispatcher = PubSubDispatcher(patterns=("chat:user:*", "group:user:*"))
        await dispatcher.start(redis)

        chat_callback = AsyncMock()
        group_callback = AsyncMock()
        await dispatcher.register(
            user_id="alice",
            connection_id="chat",
            channel_prefix="chat:user:",
            send_callback=chat_callback,
        )
        await dispatcher.register(
            user_id="alice",
            connection_id="group",
            channel_prefix="group:user:",
            send_callback=group_callback,
        )
        listen_future.set_result(
            iter(
                [
                    {
                        "type": "pmessage",
                        "channel": b"chat:user:alice",
                        "data": json.dumps({"type": "chat.message"}).encode(),
                    },
                    {
                        "type": "pmessage",
                        "channel": b"chat:user:alice",
                        "data": json.dumps({"type": "group.message.created"}).encode(),
                    },
                    {
                        "type": "pmessage",
                        "channel": b"group:user:alice",
                        "data": json.dumps({"type": "group_message"}).encode(),
                    },
                    None,
                ]
            )
        )

        await asyncio.sleep(0.1)

        assert chat_callback.await_count == 2
        group_callback.assert_awaited_once()
        chat_types = {call.args[0]["type"] for call in chat_callback.await_args_list}
        assert chat_types == {"chat.message", "group.message.created"}
        assert group_callback.await_args.args[0]["type"] == "group_message"
        await dispatcher.stop()

    @pytest.mark.asyncio
    async def test_unscoped_client_socket_receives_chat_and_group_frames(self):
        dispatcher = PubSubDispatcher()
        callback = AsyncMock()
        await dispatcher.register(
            user_id="alice",
            connection_id="events",
            send_callback=callback,
        )

        await dispatcher._dispatch_message(
            {
                "type": "pmessage",
                "channel": b"group:user:alice",
                "data": json.dumps({"type": "group_message"}).encode(),
            }
        )
        await dispatcher._dispatch_message(
            {
                "type": "pmessage",
                "channel": b"chat:user:alice",
                "data": json.dumps({"type": "chat.message"}).encode(),
            }
        )

        await asyncio.sleep(0.1)
        assert callback.await_count == 2

    @pytest.mark.asyncio
    async def test_group_action_over_shared_socket_checks_membership(self, monkeypatch):
        group_id = str(uuid4())
        websocket = AsyncMock()
        query_result = SimpleNamespace(
            all=lambda: [("alice", "alice-name"), ("another-member", "other-name")]
        )
        db = AsyncMock()
        db.execute.return_value = query_result
        publish_group_frame = AsyncMock()

        @asynccontextmanager
        async def session():
            yield db

        monkeypatch.setattr(group_ws_service, "get_async_session", session)
        monkeypatch.setattr(
            group_ws_service, "_publish_group_frame", publish_group_frame
        )

        await group_ws_service.process_group_action(
            websocket=websocket,
            redis=object(),
            message_data={
                "type": "group_typing",
                "group_id": group_id,
                "is_typing": True,
            },
            user_id="alice",
            send_lock=asyncio.Lock(),
        )

        db.execute.assert_awaited_once()
        publish_group_frame.assert_awaited_once()
        assert publish_group_frame.await_args.kwargs["member_ids"] == ["another-member"]
        assert publish_group_frame.await_args.kwargs["payload"]["data"]["username"] == (
            "alice-name"
        )

    @pytest.mark.asyncio
    async def test_group_action_over_shared_socket_rejects_non_member(
        self, monkeypatch
    ):
        group_id = str(uuid4())
        websocket = AsyncMock()
        query_result = SimpleNamespace(all=lambda: [])
        db = AsyncMock()
        db.execute.return_value = query_result
        publish_group_frame = AsyncMock()

        @asynccontextmanager
        async def session():
            yield db

        monkeypatch.setattr(group_ws_service, "get_async_session", session)
        monkeypatch.setattr(
            group_ws_service, "_publish_group_frame", publish_group_frame
        )

        await group_ws_service.process_group_action(
            websocket=websocket,
            redis=object(),
            message_data={"type": "group_typing", "group_id": group_id},
            user_id="alice",
            send_lock=asyncio.Lock(),
        )

        websocket.send_json.assert_awaited_once()
        assert websocket.send_json.await_args.args[0]["error"] == "group.access.denied"
        db.execute.assert_awaited_once()
        publish_group_frame.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_group_message_edit_broadcasts_to_active_members(self, monkeypatch):
        group_id = str(uuid4())
        message_id = str(uuid4())
        websocket = AsyncMock()
        redis = object()
        db = AsyncMock()
        members = ["alice", "bob"]
        update_result = {
            "data": {
                "message": {"id": message_id, "body": "edited"},
                "sender": {"id": "alice"},
            }
        }
        publish_group_frame = AsyncMock()

        @asynccontextmanager
        async def session():
            yield db

        monkeypatch.setattr(group_ws_service, "get_async_session", session)
        monkeypatch.setattr(
            group_ws_service, "_active_member_ids", AsyncMock(return_value=members)
        )
        monkeypatch.setattr(
            group_ws_service.group_service,
            "update_message",
            AsyncMock(return_value=update_result),
        )
        monkeypatch.setattr(
            group_ws_service, "_publish_group_frame", publish_group_frame
        )

        await group_ws_service.process_group_action(
            websocket=websocket,
            redis=redis,
            message_data={
                "type": "group_message_edit",
                "group_id": group_id,
                "message_id": message_id,
                "body": "edited",
            },
            user_id="alice",
            send_lock=asyncio.Lock(),
        )

        group_ws_service.group_service.update_message.assert_awaited_once()
        assert (
            group_ws_service.group_service.update_message.await_args.kwargs["group_id"]
            == group_id
        )
        publish_group_frame.assert_awaited_once_with(
            redis=redis,
            member_ids=members,
            payload={
                "type": "group_message_updated",
                "group_id": group_id,
                "data": update_result["data"]["message"],
                "sender": update_result["data"]["sender"],
            },
        )

    @pytest.mark.asyncio
    async def test_dm_message_edit_fans_out_to_both_participants(self, monkeypatch):
        sender_id = str(uuid4())
        recipient_id = str(uuid4())
        result = {
            "sender_id": sender_id,
            "recipient_id": recipient_id,
            "message": {"id": str(uuid4()), "body": "edited"},
        }
        db = AsyncMock()

        @asynccontextmanager
        async def session():
            yield db

        class Pipeline:
            def __init__(self):
                self.published = []

            async def __aenter__(self):
                return self

            async def __aexit__(self, *_):
                return None

            def publish(self, channel, payload):
                self.published.append((channel, json.loads(payload)))

            async def execute(self):
                return None

        class Redis:
            def __init__(self):
                self.pipe = Pipeline()

            def pipeline(self):
                return self.pipe

        redis = Redis()
        monkeypatch.setattr(mobile_events_service, "get_async_session", session)
        monkeypatch.setattr(
            mobile_events_service.chat_service,
            "edit_message",
            AsyncMock(return_value=result),
        )

        await mobile_events_service.MobileEventsService()._handle_chat_message_mutation(
            websocket=AsyncMock(),
            send_lock=asyncio.Lock(),
            redis=redis,
            user_id=sender_id,
            incoming={"message_id": str(uuid4()), "body": "edited"},
            msg_type="chat.edit",
        )

        assert [channel for channel, _ in redis.pipe.published] == [
            f"chat:user:{sender_id}",
            f"chat:user:{recipient_id}",
        ]
        assert all(
            frame["type"] == "chat.message.updated"
            and frame["data"] == result["message"]
            for _, frame in redis.pipe.published
        )

    @pytest.mark.asyncio
    async def test_dispatch_skips_unregistered_user(self, mock_redis):
        """Messages for users without a registered callback are silently dropped."""
        redis, pubsub = mock_redis
        listen_future = asyncio.Future()
        pubsub.listen.return_value = listen_future

        dispatcher = PubSubDispatcher()
        await dispatcher.start(redis)

        msg = {
            "type": "pmessage",
            "channel": b"chat:user:ghost",
            "data": json.dumps({"type": "chat.message"}).encode(),
        }
        listen_future.set_result(iter([msg, None]))

        await asyncio.sleep(0.1)
        await dispatcher.stop()

    @pytest.mark.asyncio
    async def test_dispatch_handles_malformed_json(self, mock_redis):
        """Malformed JSON payloads must not crash the dispatcher."""
        redis, pubsub = mock_redis
        listen_future = asyncio.Future()
        pubsub.listen.return_value = listen_future

        dispatcher = PubSubDispatcher()
        await dispatcher.start(redis)

        callback = AsyncMock()
        await dispatcher.register(user_id="user-1", send_callback=callback)

        msg = {
            "type": "pmessage",
            "channel": b"chat:user:user-1",
            "data": b"not-valid-json{{{",
        }
        listen_future.set_result(iter([msg, None]))

        await asyncio.sleep(0.1)
        callback.assert_not_called()

        await dispatcher.stop()

    @pytest.mark.asyncio
    async def test_dispatch_handles_non_pmesssage_messages(self, mock_redis):
        """Subscription/unsubscription confirmation messages (non-pmessage)
        must be ignored."""
        redis, pubsub = mock_redis
        listen_future = asyncio.Future()
        pubsub.listen.return_value = listen_future

        dispatcher = PubSubDispatcher()
        await dispatcher.start(redis)

        callback = AsyncMock()
        await dispatcher.register(user_id="user-1", send_callback=callback)

        msg = {
            "type": "message",
            "channel": b"chat:user:user-1",
            "data": b"{}",
        }
        listen_future.set_result(iter([msg, None]))

        await asyncio.sleep(0.1)
        callback.assert_not_called()

        await dispatcher.stop()

    @pytest.mark.asyncio
    async def test_module_level_dispatcher_is_singleton(self):
        """The module-level ``pubsub_dispatcher`` is a single shared instance."""
        assert pubsub_dispatcher is not None
        assert isinstance(pubsub_dispatcher, PubSubDispatcher)


class TestCatchupChatStream:
    """Verify the one-time stream catch-up behaves correctly."""

    @pytest.mark.asyncio
    async def test_catchup_reads_non_blocking(self):
        """_catchup_chat_stream must omit BLOCK so it returns immediately.

        Passing ``block=0`` to redis-py emits ``XREAD ... BLOCK 0``, which
        blocks forever on an empty stream and would stall ``chat.ready``.
        """
        from app.service.ws_presence import PresenceManager

        manager = PresenceManager()
        redis = AsyncMock()
        redis.get.return_value = None
        redis.xrevrange.return_value = []
        redis.xread.return_value = []

        websocket = AsyncMock()
        send_lock = asyncio.Lock()

        await manager._catchup_chat_stream(
            websocket=websocket,
            redis=redis,
            user_id="user-1",
            send_lock=send_lock,
        )

        redis.xread.assert_called_once()
        call_kwargs = redis.xread.call_args.kwargs
        assert call_kwargs["block"] is None
        assert call_kwargs["count"] == 100

    @pytest.mark.asyncio
    async def test_catchup_delivers_messages(self):
        """Messages in the stream should be delivered to the WebSocket."""
        from app.service.ws_presence import PresenceManager

        manager = PresenceManager()
        redis = AsyncMock()
        redis.get.return_value = None
        redis.xrevrange.return_value = []

        msg_id = "123-456"
        payload_bytes = {
            "type": b"chat.message",
            "data": b'{"type": "chat.message", "data": {"id": "msg-1", "body": "Hello"}}',
        }
        redis.xread.return_value = [
            ("chat:events:stream:user-1", [(msg_id, payload_bytes)])
        ]

        websocket = AsyncMock()
        send_lock = asyncio.Lock()

        await manager._catchup_chat_stream(
            websocket=websocket,
            redis=redis,
            user_id="user-1",
            send_lock=send_lock,
        )

        # send_json is called via _send_json_safe which catches RuntimeError
        # and returns False. We verify it was called.
        websocket.send_json.assert_called_once()

    @pytest.mark.asyncio
    async def test_catchup_skips_non_chat_messages(self):
        """Non-chat-message events in the stream are skipped (cursor advanced)."""
        from app.service.ws_presence import PresenceManager

        manager = PresenceManager()
        redis = AsyncMock()
        redis.get.return_value = None
        redis.xrevrange.return_value = []

        payload_bytes = {
            "type": b"some.other.event",
            "data": b"{}",
        }
        msg_id = "123-456"
        redis.xread.return_value = [
            ("chat:events:stream:user-1", [(msg_id, payload_bytes)])
        ]

        websocket = AsyncMock()
        send_lock = asyncio.Lock()

        await manager._catchup_chat_stream(
            websocket=websocket,
            redis=redis,
            user_id="user-1",
            send_lock=send_lock,
        )

        websocket.send_json.assert_not_called()
        redis.set.assert_called()

    @pytest.mark.asyncio
    async def test_catchup_skips_already_delivered_messages(self):
        """Messages already delivered by the queue path should be skipped."""
        from app.service.ws_presence import PresenceManager

        manager = PresenceManager()
        redis = AsyncMock()
        redis.get.return_value = None
        redis.xrevrange.return_value = []

        payload_bytes = {
            "type": b"chat.message",
            "data": b'{"type": "chat.message", "data": {"id": "msg-1", "recipient_id": "user-1"}}',
        }
        msg_id = "123-456"
        redis.xread.return_value = [
            ("chat:events:stream:user-1", [(msg_id, payload_bytes)])
        ]
        manager._should_deliver_chat_message = AsyncMock(return_value=False)

        websocket = AsyncMock()
        send_lock = asyncio.Lock()

        await manager._catchup_chat_stream(
            websocket=websocket,
            redis=redis,
            user_id="user-1",
            send_lock=send_lock,
        )

        websocket.send_json.assert_not_called()
        redis.set.assert_called()

    @pytest.mark.asyncio
    async def test_catchup_stops_on_send_failure(self):
        """If sending fails (connection dead), stop trying — don't advance cursor."""
        from app.service.ws_presence import PresenceManager

        manager = PresenceManager()
        redis = AsyncMock()
        redis.get.return_value = None
        redis.xrevrange.return_value = []

        payload_bytes = {
            "type": b"chat.message",
            "data": b'{"type": "chat.message", "data": {"id": "msg-1", "recipient_id": "user-1"}}',
        }
        msg_id = "123-456"
        redis.xread.return_value = [
            ("chat:events:stream:user-1", [(msg_id, payload_bytes)])
        ]
        manager._should_deliver_chat_message = AsyncMock(return_value=True)

        websocket = AsyncMock()
        websocket.send_json.side_effect = RuntimeError("connection closed")

        send_lock = asyncio.Lock()

        await manager._catchup_chat_stream(
            websocket=websocket,
            redis=redis,
            user_id="user-1",
            send_lock=send_lock,
        )

        websocket.send_json.assert_called_once()
        redis.set.assert_not_called()


class TestConnectionPresence:
    @pytest.mark.asyncio
    async def test_presence_stays_online_until_last_connection_closes(self):
        class PresenceRedis:
            def __init__(self):
                self.connections = {}
                self.status = {}

            async def eval(
                self,
                script,
                _key_count,
                connection_key,
                status_key,
                now,
                connection_id,
                ttl,
            ):
                now = int(now)
                ttl = int(ttl)
                active = {
                    connection: expires_at
                    for connection, expires_at in self.connections.get(
                        connection_key, {}
                    ).items()
                    if expires_at > now
                }

                if "ZADD" in script:
                    was_online = bool(active)
                    active[connection_id] = now + ttl
                    self.connections[connection_key] = active
                    self.status[status_key] = "1"
                    return int(was_online)

                active.pop(connection_id, None)
                if active:
                    self.connections[connection_key] = active
                    self.status[status_key] = "1"
                else:
                    self.connections.pop(connection_key, None)
                    self.status.pop(status_key, None)
                return len(active)

        redis = PresenceRedis()
        manager = PresenceManager()

        assert await manager._register_presence_connection(
            redis=redis,
            user_id="user-1",
            connection_id="phone",
        )
        assert not await manager._register_presence_connection(
            redis=redis,
            user_id="user-1",
            connection_id="browser",
        )
        assert not await manager._remove_presence_connection(
            redis=redis,
            user_id="user-1",
            connection_id="phone",
        )
        assert redis.status["presence:user:user-1"] == "1"
        assert await manager._remove_presence_connection(
            redis=redis,
            user_id="user-1",
            connection_id="browser",
        )
        assert "presence:user:user-1" not in redis.status


class TestMobileEventPrivacy:
    @pytest.mark.asyncio
    async def test_read_mobile_events_only_returns_the_current_users_events(self):
        from app.service.ws_presence import PresenceManager

        manager = PresenceManager()
        redis = AsyncMock()
        redis.xread.return_value = [
            (
                "mobile:events:stream",
                [
                    (
                        "1-0",
                        {
                            "payload": json.dumps(
                                {"user_id": "another-user", "progress": 25}
                            )
                        },
                    ),
                    (
                        "2-0",
                        {
                            "payload": json.dumps(
                                {"user_id": "current-user", "progress": 100}
                            )
                        },
                    ),
                ],
            )
        ]

        result = await manager.read_mobile_events(
            redis=redis,
            user_id="current-user",
            last_id="0-0",
            block_ms=0,
            count=50,
        )

        assert [item["id"] for item in result["items"]] == ["2-0"]
        assert result["next_last_id"] == "2-0"


class TestBlockingMobileReadIsolation:
    """The long-poll must never hold more pool connections than it has slots."""

    @pytest.mark.asyncio
    async def test_uses_block_when_a_slot_is_available(self):
        from app.service.ws_presence import PresenceManager

        manager = PresenceManager()
        redis = AsyncMock()
        redis.xread.return_value = []

        await manager.read_mobile_events(
            redis=redis,
            user_id="current-user",
            last_id="0-0",
            block_ms=25000,
            count=50,
        )

        assert redis.xread.call_args.kwargs["block"] == 25000

    @pytest.mark.asyncio
    async def test_saturated_slots_fall_back_to_non_blocking(self, monkeypatch):
        """When every blocking slot is taken, the read must not block."""
        from app.service import ws_presence
        from app.service.ws_presence import PresenceManager

        exhausted = asyncio.Semaphore(1)
        await exhausted.acquire()
        monkeypatch.setattr(ws_presence, "_BLOCKING_READ_SLOTS", exhausted)

        manager = PresenceManager()
        redis = AsyncMock()
        redis.xread.return_value = []

        await manager.read_mobile_events(
            redis=redis,
            user_id="current-user",
            last_id="0-0",
            block_ms=25000,
            count=50,
        )

        assert redis.xread.call_args.kwargs["block"] is None

    @pytest.mark.asyncio
    async def test_pool_exhaustion_returns_empty_not_an_error(self):
        """A saturated Redis pool must degrade to an empty batch, not raise."""
        from redis.exceptions import ConnectionError as RedisConnectionError

        from app.service.ws_presence import PresenceManager

        manager = PresenceManager()
        redis = AsyncMock()
        redis.xread.side_effect = RedisConnectionError("Too many connections")

        result = await manager.read_mobile_events(
            redis=redis,
            user_id="current-user",
            last_id="5-0",
            block_ms=25000,
            count=50,
        )

        assert result == {"status": "success", "items": [], "next_last_id": "5-0"}


class TestRedisConnectionBudget:
    """The two Redis pools must never exceed the provider's connection cap."""

    def test_limit_zero_leaves_pools_untouched(self):
        from app.core.config import Settings

        s = Settings(
            REDIS_CONNECTION_LIMIT=0,
            REDIS_MAX_CONNECTIONS=50,
            REDIS_BLOCKING_MAX_CONNECTIONS=20,
        )
        assert (s.REDIS_MAX_CONNECTIONS, s.REDIS_BLOCKING_MAX_CONNECTIONS) == (50, 20)

    def test_limit_shrinks_pools_to_fit(self):
        from app.core.config import Settings

        s = Settings(
            REDIS_CONNECTION_LIMIT=10,
            REDIS_MAX_CONNECTIONS=50,
            REDIS_BLOCKING_MAX_CONNECTIONS=20,
        )
        assert s.REDIS_MAX_CONNECTIONS + s.REDIS_BLOCKING_MAX_CONNECTIONS == 10
        assert s.REDIS_MAX_CONNECTIONS >= 1
        assert s.REDIS_BLOCKING_MAX_CONNECTIONS >= 1
        # Blocking pool is trimmed first; the shared pool gets the remainder.
        assert s.REDIS_BLOCKING_MAX_CONNECTIONS == 2
        assert s.REDIS_MAX_CONNECTIONS == 8

    def test_minimum_limit_of_two(self):
        from app.core.config import Settings

        s = Settings(
            REDIS_CONNECTION_LIMIT=2,
            REDIS_MAX_CONNECTIONS=50,
            REDIS_BLOCKING_MAX_CONNECTIONS=20,
        )
        assert (s.REDIS_MAX_CONNECTIONS, s.REDIS_BLOCKING_MAX_CONNECTIONS) == (1, 1)

    def test_limit_of_one_warns(self):
        from app.core.config import Settings

        with pytest.warns(UserWarning):
            s = Settings(
                REDIS_CONNECTION_LIMIT=1,
                REDIS_MAX_CONNECTIONS=50,
                REDIS_BLOCKING_MAX_CONNECTIONS=20,
            )
        assert (s.REDIS_MAX_CONNECTIONS, s.REDIS_BLOCKING_MAX_CONNECTIONS) == (1, 1)

    def test_config_that_already_fits_is_unchanged(self):
        from app.core.config import Settings

        s = Settings(
            REDIS_CONNECTION_LIMIT=10,
            REDIS_MAX_CONNECTIONS=6,
            REDIS_BLOCKING_MAX_CONNECTIONS=4,
        )
        assert (s.REDIS_MAX_CONNECTIONS, s.REDIS_BLOCKING_MAX_CONNECTIONS) == (6, 4)

    @pytest.mark.asyncio
    async def test_limit_of_one_shares_the_main_client(self, monkeypatch):
        from app.db import redis as redis_db

        sentinel = object()

        async def fake_main_client():
            return sentinel

        monkeypatch.setattr(redis_db.settings, "REDIS_CONNECTION_LIMIT", 1)
        monkeypatch.setattr(redis_db, "get_redis_client", fake_main_client)
        assert await redis_db.get_blocking_redis_client() is sentinel
