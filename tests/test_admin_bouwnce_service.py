from __future__ import annotations

import asyncio
import importlib
import sys
from datetime import UTC, datetime
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch
from uuid import UUID, uuid4

from app.matching_ground.schema.chat import ChatMessageData


class _ScalarResult:
    def __init__(self, values: list[UUID]) -> None:
        self._values = values

    def scalars(self) -> "_ScalarResult":
        return self

    def all(self) -> list[UUID]:
        return self._values

    def scalar_one_or_none(self):
        return self._values[0] if self._values else None


class _FakeDb:
    def __init__(self, values: list[UUID]) -> None:
        self._values = values
        self.commit = AsyncMock()

    async def execute(self, _stmt):
        return _ScalarResult(self._values)


def _load_admin_service(monkeypatch):
    models_pkg = sys.modules.get("app.models")
    if models_pkg is None:
        import types

        models_pkg = types.ModuleType("app.models")
        models_pkg.__path__ = [
            str(Path(__file__).resolve().parents[1] / "app" / "models")
        ]
        monkeypatch.setitem(sys.modules, "app.models", models_pkg)

    basemodel = importlib.import_module("app.models.basemodel")
    models_pkg.BaseModel = basemodel.BaseModel

    module = importlib.import_module(
        "app.matching_ground.service.admin_bouwnce_service"
    )
    return module.admin_bouwnce_service, module


def _chat_message(
    *, conversation_id: UUID, sender_id: UUID, recipient_id: UUID
) -> ChatMessageData:
    message_id = uuid4()
    now = datetime.now(UTC)
    return ChatMessageData(
        conversation_id=conversation_id,
        sender_id=sender_id,
        recipient_id=recipient_id,
        body="Hello from Bouwnce",
        read_at=None,
        media_type=None,
        media_urls=None,
        media_name=None,
        reply_to_message_id=None,
        id=message_id,
        created_at=now,
        updated_at=now,
        sender=None,
        recipient=None,
        reply_to_message=False,
    )


def test_admin_bouwnce_send_message_uses_message_model_id(monkeypatch) -> None:
    admin_bouwnce_service, module = _load_admin_service(monkeypatch)
    system_user_id = uuid4()
    target_user_id = uuid4()
    system_user = SimpleNamespace(
        id=system_user_id,
        email="support@bouwnce.com",
        username="bouwnce",
        full_name="Bouwnce Support",
    )
    db = _FakeDb([target_user_id])
    redis = object()
    body = "Welcome to Bouwnce"
    conversation_id = uuid4()
    message = _chat_message(
        conversation_id=conversation_id,
        sender_id=system_user_id,
        recipient_id=target_user_id,
    )
    send_calls: list[dict] = []

    async def _send_message(**kwargs):
        send_calls.append(kwargs)
        return {"conversation_id": str(conversation_id), "message": message}

    with (
        patch.object(
            module.bouwnce_dm_service,
            "get_system_user",
            new=AsyncMock(return_value=system_user),
        ),
        patch.object(
            module.bouwnce_dm_service,
            "ensure_welcome_conversation",
            new=AsyncMock(),
        ),
        patch.object(
            module.chat_service,
            "send_message",
            new=_send_message,
        ),
    ):
        result = asyncio.run(
            admin_bouwnce_service.send_message(
                db=db,
                redis=redis,
                user_ids=[str(target_user_id)],
                body=body,
                all_users=False,
            )
        )

    assert result["status"] == "success"
    assert result["status_code"] == 201
    assert result["message"] == "Bouwnce messages sent"
    assert result["data"]["count"] == 1
    assert [item["user_id"] for item in result["data"]["items"]] == [
        str(target_user_id)
    ]
    assert result["data"]["items"][0]["conversation_id"] == str(conversation_id)
    assert result["data"]["items"][0]["message_id"] == str(message.id)
    assert [call["recipient_id"] for call in send_calls] == [str(target_user_id)]
    assert db.commit.await_count == 1
    assert len(send_calls) == 1
