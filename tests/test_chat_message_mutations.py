from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest

# Load the model/service graph through the same entry point used by socket tests.
from app.service import group_ws_service  # noqa: F401
from app.utils.exception import ForbiddenException, NotFoundException


def _chat_service():
    from app.matching_ground.service.chat_service import ChatService

    return ChatService()


@pytest.mark.asyncio
async def test_edit_message_updates_only_the_sender_message(monkeypatch):
    sender_id = str(uuid4())
    message = SimpleNamespace(
        id=uuid4(),
        conversation_id=uuid4(),
        sender_id=sender_id,
        recipient_id=str(uuid4()),
    )
    repository = AsyncMock()
    repository.find_message.return_value = message
    repository.update_message_body.return_value = message
    repository.get_users.return_value = [
        SimpleNamespace(id=sender_id),
        SimpleNamespace(id=message.recipient_id),
    ]
    monkeypatch.setattr(
        "app.matching_ground.service.chat_service.chat_repository", repository
    )

    service = _chat_service()
    serialized = SimpleNamespace(model_dump=lambda **_: {"id": str(message.id)})
    monkeypatch.setattr(service, "_build_chat_message_data", lambda **_: serialized)
    db = AsyncMock()

    result = await service.edit_message(
        db=db,
        message_id=str(message.id),
        user_id=sender_id,
        body="  corrected text  ",
    )

    repository.update_message_body.assert_awaited_once_with(
        db, str(message.id), "corrected text"
    )
    db.commit.assert_awaited_once()
    assert result["message"] == {"id": str(message.id)}


@pytest.mark.asyncio
async def test_edit_message_rejects_non_sender(monkeypatch):
    message = SimpleNamespace(sender_id=str(uuid4()))
    repository = AsyncMock()
    repository.find_message.return_value = message
    monkeypatch.setattr(
        "app.matching_ground.service.chat_service.chat_repository", repository
    )

    with pytest.raises(ForbiddenException):
        await _chat_service().edit_message(
            db=AsyncMock(),
            message_id=str(uuid4()),
            user_id=str(uuid4()),
            body="unauthorized edit",
        )

    repository.update_message_body.assert_not_awaited()


@pytest.mark.asyncio
async def test_delete_message_removes_only_the_sender_message(monkeypatch):
    sender_id = str(uuid4())
    message = SimpleNamespace(
        id=uuid4(),
        conversation_id=uuid4(),
        sender_id=sender_id,
        recipient_id=str(uuid4()),
    )
    repository = AsyncMock()
    repository.find_message.return_value = message
    repository.delete_message.return_value = True
    monkeypatch.setattr(
        "app.matching_ground.service.chat_service.chat_repository", repository
    )
    db = AsyncMock()

    result = await _chat_service().delete_message(
        db=db, message_id=str(message.id), user_id=sender_id
    )

    repository.delete_message.assert_awaited_once_with(db, str(message.id))
    db.commit.assert_awaited_once()
    assert result["message_id"] == str(message.id)
    assert result["recipient_id"] == message.recipient_id


@pytest.mark.asyncio
async def test_group_edit_rejects_message_outside_requested_group(monkeypatch):
    message = SimpleNamespace(group_id=str(uuid4()))
    repository = AsyncMock()
    repository.get_message_by_id.return_value = message
    group_service = group_ws_service.group_service
    monkeypatch.setattr(group_service, "message_repo", repository)
    db = AsyncMock()

    with pytest.raises(NotFoundException):
        await group_service.update_message(
            db=db,
            group_id=str(uuid4()),
            message_id=str(uuid4()),
            user_id=str(uuid4()),
            body="edited",
        )

    repository.update_message.assert_not_awaited()
    db.rollback.assert_awaited_once()
