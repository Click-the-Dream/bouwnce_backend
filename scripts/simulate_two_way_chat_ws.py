from __future__ import annotations

import asyncio
import contextlib
import json
import uuid
from dataclasses import dataclass, field
from types import SimpleNamespace

from starlette.datastructures import QueryParams
from starlette.websockets import WebSocketDisconnect

import app.service.mobile_events_service as mobile_events_module


@dataclass
class FakePubSub:
    channels: set[str] = field(default_factory=set)
    queue: asyncio.Queue = field(default_factory=asyncio.Queue)
    closed: bool = False

    async def subscribe(self, *channels):
        self.channels.update(str(channel) for channel in channels)

    async def unsubscribe(self, *channels):
        if channels:
            for channel in channels:
                self.channels.discard(str(channel))
        else:
            self.channels.clear()

    async def close(self):
        self.closed = True
        await self.queue.put(None)

    async def listen(self):
        while True:
            item = await self.queue.get()
            if item is None:
                return
            yield item


class FakeRedis:
    def __init__(self):
        self.pubsubs: list[FakePubSub] = []
        self.store: dict[str, str] = {}

    def pubsub(self):
        pubsub = FakePubSub()
        self.pubsubs.append(pubsub)
        return pubsub

    async def publish(self, channel, payload):
        for pubsub in list(self.pubsubs):
            if not pubsub.closed and channel in pubsub.channels:
                await pubsub.queue.put(
                    {"type": "message", "channel": channel, "data": payload}
                )

    async def xread(self, *args, **kwargs):
        return []

    async def set(self, key, value, ex=None):
        self.store[key] = value

    async def get(self, key):
        return self.store.get(key)

    async def delete(self, key):
        self.store.pop(key, None)

    async def mget(self, *keys):
        return [self.store.get(key) for key in keys]


@contextlib.asynccontextmanager
async def fake_session():
    yield SimpleNamespace()


class FakeWebSocket:
    def __init__(self, token: str, incoming: list[str] | None = None):
        self.query_params = QueryParams({"token": token})
        self._incoming = asyncio.Queue()
        for item in incoming or []:
            self._incoming.put_nowait(item)
        self.sent: list[dict | str] = []
        self.accepted = False

    async def accept(self):
        self.accepted = True

    async def receive_text(self):
        item = await self._incoming.get()
        if item == "__close__":
            raise WebSocketDisconnect(code=1000)
        return item

    async def send_json(self, payload):
        self.sent.append(payload)

    async def send_text(self, payload):
        self.sent.append(payload)

    async def close(self, code=1000):
        return None

    def close_later(self):
        self._incoming.put_nowait("__close__")


async def noop(*args, **kwargs):
    return None


async def main():
    sender_id = str(uuid.uuid4())
    recipient_id = str(uuid.uuid4())
    fake_redis = FakeRedis()

    sender_user = SimpleNamespace(
        id=uuid.UUID(sender_id),
        username="sender",
        full_name="Sender User",
    )
    recipient_user = SimpleNamespace(
        id=uuid.UUID(recipient_id),
        username="recipient",
        full_name="Recipient User",
    )

    def fake_verify_token_sender(_token):
        return {"type": "access", "sub": sender_id}

    def fake_verify_token_recipient(_token):
        return {"type": "access", "sub": recipient_id}

    async def fake_get_redis_client():
        return fake_redis

    async def fake_get_by_id(user_id, db):
        return sender_user if str(user_id) == sender_id else recipient_user

    async def fake_get_conversation_partner_ids(*, db, user_id):
        return [recipient_id]

    async def fake_send_message(
        *,
        db,
        redis,
        sender,
        recipient_id,
        body,
        reply_to_message_id=None,
        commit=True,
        as_response=False,
    ):
        payload = {
            "type": "chat.message",
            "data": {
                "conversation_id": "conv-1",
                "message": {
                    "id": "msg-1",
                    "body": body,
                    "reply_to_message": False,
                },
            },
        }
        payload_json = json.dumps(payload)
        await redis.publish(f"chat:user:{sender.id}", payload_json)
        await redis.publish(f"chat:user:{recipient_id}", payload_json)
        return payload["data"]

    old = {
        "verify_token": mobile_events_module.verify_token,
        "get_redis_client": mobile_events_module.get_redis_client,
        "get_async_session": mobile_events_module.get_async_session,
        "User_get_by_id": mobile_events_module.User.get_by_id,
        "send_message": mobile_events_module.chat_service.send_message,
        "presence_snapshot": mobile_events_module.MobileEventsService._send_presence_snapshot,
        "presence_heartbeat": mobile_events_module.MobileEventsService._presence_heartbeat,
        "get_system_user": mobile_events_module.bouwnce_dm_service.get_system_user,
        "ensure_welcome": mobile_events_module.bouwnce_dm_service.ensure_welcome_conversation,
        "get_conversation_partner_ids": mobile_events_module.chat_service.get_conversation_partner_ids,
    }

    mobile_events_module.get_redis_client = fake_get_redis_client
    mobile_events_module.get_async_session = fake_session
    mobile_events_module.User.get_by_id = fake_get_by_id
    mobile_events_module.chat_service.send_message = fake_send_message
    mobile_events_module.MobileEventsService._send_presence_snapshot = noop
    mobile_events_module.MobileEventsService._presence_heartbeat = noop
    mobile_events_module.bouwnce_dm_service.get_system_user = lambda db: None
    mobile_events_module.bouwnce_dm_service.ensure_welcome_conversation = noop
    mobile_events_module.chat_service.get_conversation_partner_ids = (
        fake_get_conversation_partner_ids
    )

    try:
        service = mobile_events_module.MobileEventsService()
        recipient_ws = FakeWebSocket(token=f"recipient-{uuid.uuid4().hex}")
        sender_ws = FakeWebSocket(
            token=f"sender-{uuid.uuid4().hex}",
            incoming=[
                json.dumps(
                    {
                        "type": "chat.send",
                        "recipient_id": recipient_id,
                        "body": "hello from terminal test",
                        "client_id": "c1",
                    }
                )
            ],
        )

        async def run_recipient():
            mobile_events_module.verify_token = fake_verify_token_recipient
            await service.handle_ws(recipient_ws)

        async def run_sender():
            mobile_events_module.verify_token = fake_verify_token_sender
            await service.handle_ws(sender_ws)

        recipient_task = asyncio.create_task(run_recipient())
        await asyncio.sleep(0.05)
        sender_task = asyncio.create_task(run_sender())

        for _ in range(120):
            if any(
                isinstance(item, dict) and item.get("type") == "chat.message"
                for item in recipient_ws.sent
            ):
                break
            await asyncio.sleep(0.05)
        else:
            raise RuntimeError("recipient did not receive chat.message")

        sender_task.cancel()
        recipient_task.cancel()
        with contextlib.suppress(Exception):
            await sender_task
        with contextlib.suppress(Exception):
            await recipient_task

        print("SENDER_MESSAGES:", json.dumps(sender_ws.sent, indent=2))
        print("RECIPIENT_MESSAGES:", json.dumps(recipient_ws.sent, indent=2))
        print(
            "RESULT:",
            {
                "sender_ack": any(
                    isinstance(item, dict) and item.get("type") == "chat.sent"
                    for item in sender_ws.sent
                ),
                "recipient_message": any(
                    isinstance(item, dict) and item.get("type") == "chat.message"
                    for item in recipient_ws.sent
                ),
            },
        )
    finally:
        mobile_events_module.verify_token = old["verify_token"]
        mobile_events_module.get_redis_client = old["get_redis_client"]
        mobile_events_module.get_async_session = old["get_async_session"]
        mobile_events_module.User.get_by_id = old["User_get_by_id"]
        mobile_events_module.chat_service.send_message = old["send_message"]
        mobile_events_module.MobileEventsService._send_presence_snapshot = old[
            "presence_snapshot"
        ]
        mobile_events_module.MobileEventsService._presence_heartbeat = old[
            "presence_heartbeat"
        ]
        mobile_events_module.bouwnce_dm_service.get_system_user = old["get_system_user"]
        mobile_events_module.bouwnce_dm_service.ensure_welcome_conversation = old[
            "ensure_welcome"
        ]
        mobile_events_module.chat_service.get_conversation_partner_ids = old[
            "get_conversation_partner_ids"
        ]


if __name__ == "__main__":
    asyncio.run(main())
