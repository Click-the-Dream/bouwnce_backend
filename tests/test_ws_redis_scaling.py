"""Tests for the Phase 1 Redis connection scaling refactoring.

Covers:
- PubSubDispatcher: single psubscribe, dispatch to correct user, unregister
- _catchup_chat_stream: one-time non-blocking XREAD, no persistent connection
"""

from __future__ import annotations

import asyncio
import json
from unittest.mock import AsyncMock

import pytest

from app.service.ws_presence import PubSubDispatcher, pubsub_dispatcher


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

        # psubscribe is a coroutine; make it a no-op coroutine that returns the pubsub
        async def _noop_psubscribe(*a, **kw):
            return pubsub

        pubsub.psubscribe = _noop_psubscribe
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
            # psubscribe called with correct pattern
            # (the coroutine was awaited via ensure_future)
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
    async def test_catchup_reads_with_block_zero(self):
        """_catchup_chat_stream must use block=0 (non-blocking)."""
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
        assert call_kwargs["block"] == 0
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
