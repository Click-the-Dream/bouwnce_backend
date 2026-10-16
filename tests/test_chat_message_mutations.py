from __future__ import annotations

from datetime import UTC, datetime, timedelta
from types import SimpleNamespace
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest

# Load the model/service graph through the same entry point used by socket tests.
from app.service import group_ws_service  # noqa: F401
from app.utils.exception import (
    BadRequestException,
    ForbiddenException,
    NotFoundException,
)


def _chat_service():
    from app.matching_ground.service.chat_service import ChatService

    return ChatService()


@pytest.mark.asyncio
async def test_edit_message_updates_only_the_sender_message(monkeypatch):
    from app.core.config import settings

    sender_id = str(uuid4())
    message = SimpleNamespace(
        id=uuid4(),
        conversation_id=uuid4(),
        sender_id=sender_id,
        recipient_id=str(uuid4()),
        created_at=datetime.now(UTC),
        deleted_for_everyone_at=None,
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

    repository.update_message_body.assert_awaited_once()
    edit_args = repository.update_message_body.await_args.args
    assert edit_args[:4] == (db, str(message.id), "corrected text", sender_id)
    assert (
        datetime.now(UTC) - timedelta(seconds=settings.MESSAGE_EDIT_TIMEOUT_SECONDS + 1)
        < edit_args[4]
    )
    assert edit_args[4] <= datetime.now(UTC)
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
async def test_edit_message_rejects_messages_outside_configured_window(monkeypatch):
    from app.core.config import settings

    message = SimpleNamespace(
        id=uuid4(),
        sender_id=str(uuid4()),
        created_at=datetime.now(UTC)
        - timedelta(seconds=settings.MESSAGE_EDIT_TIMEOUT_SECONDS + 1),
        deleted_for_everyone_at=None,
    )
    repository = AsyncMock()
    repository.find_message.return_value = message
    monkeypatch.setattr(
        "app.matching_ground.service.chat_service.chat_repository", repository
    )

    with pytest.raises(BadRequestException, match="edit window expired"):
        await _chat_service().edit_message(
            db=AsyncMock(),
            message_id=str(message.id),
            user_id=message.sender_id,
            body="too late",
        )

    repository.update_message_body.assert_not_awaited()


@pytest.mark.asyncio
async def test_delete_for_everyone_keeps_message_tombstone(monkeypatch):
    from app.core.config import settings

    sender_id = str(uuid4())
    message = SimpleNamespace(
        id=uuid4(),
        conversation_id=uuid4(),
        sender_id=sender_id,
        recipient_id=str(uuid4()),
        created_at=datetime.now(UTC),
        deleted_for_everyone_at=None,
    )
    repository = AsyncMock()
    repository.find_message.return_value = message
    repository.delete_for_everyone.return_value = message
    monkeypatch.setattr(
        "app.matching_ground.service.chat_service.chat_repository", repository
    )
    db = AsyncMock()

    result = await _chat_service().delete_message(
        db=db, message_id=str(message.id), user_id=sender_id
    )

    repository.delete_for_everyone.assert_awaited_once()
    delete_after = repository.delete_for_everyone.await_args.args[3]
    expected_cutoff = datetime.now(UTC) - timedelta(
        seconds=settings.MESSAGE_DELETE_EVERYONE_TIMEOUT_SECONDS
    )
    assert (
        expected_cutoff - timedelta(seconds=1)
        <= delete_after
        <= (expected_cutoff + timedelta(seconds=1))
    )
    db.commit.assert_awaited_once()
    assert result["message_id"] == str(message.id)
    assert result["recipient_id"] == message.recipient_id
    assert result["deleted_for"] == [sender_id, message.recipient_id]


@pytest.mark.asyncio
async def test_delete_for_me_hides_message_from_only_requesting_user(monkeypatch):
    sender_id = str(uuid4())
    recipient_id = str(uuid4())
    message = SimpleNamespace(
        id=uuid4(),
        conversation_id=uuid4(),
        sender_id=sender_id,
        recipient_id=recipient_id,
    )
    repository = AsyncMock()
    repository.find_message.return_value = message
    monkeypatch.setattr(
        "app.matching_ground.service.chat_service.chat_repository", repository
    )

    db = AsyncMock()
    result = await _chat_service().delete_message(
        db=db,
        message_id=str(message.id),
        user_id=recipient_id,
        delete_for="me",
    )

    repository.delete_for_user.assert_awaited_once_with(
        db, str(message.id), recipient_id
    )
    repository.delete_for_everyone.assert_not_awaited()
    assert result["deleted_for"] == [recipient_id]


@pytest.mark.asyncio
async def test_group_edit_rejects_message_outside_requested_group(monkeypatch):
    message = SimpleNamespace(group_id=str(uuid4()))
    repository = AsyncMock()
    repository.get_message_by_id.return_value = message
    group_service = group_ws_service.group_service
    monkeypatch.setattr(group_service, "message_repo", repository)
    monkeypatch.setattr(group_service, "member_repo", AsyncMock())
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


@pytest.mark.asyncio
async def test_group_edit_rejects_message_outside_configured_window(monkeypatch):
    from app.core.config import settings

    group_service = group_ws_service.group_service
    group_id = str(uuid4())
    sender_id = str(uuid4())
    message = SimpleNamespace(
        group_id=group_id,
        sender_id=sender_id,
        created_at=datetime.now(UTC)
        - timedelta(seconds=settings.MESSAGE_EDIT_TIMEOUT_SECONDS + 1),
        deleted_for_everyone_at=None,
    )
    repository = AsyncMock()
    repository.get_message_by_id.return_value = message
    monkeypatch.setattr(group_service, "message_repo", repository)
    members = AsyncMock()
    members.get_member.return_value = SimpleNamespace(is_active=True)
    monkeypatch.setattr(group_service, "member_repo", members)

    with pytest.raises(BadRequestException, match="edit window expired"):
        await group_service.update_message(
            db=AsyncMock(),
            group_id=group_id,
            message_id=str(uuid4()),
            user_id=sender_id,
            body="too late",
        )

    repository.update_message.assert_not_awaited()


@pytest.mark.asyncio
async def test_group_delete_for_me_hides_only_for_requesting_member(monkeypatch):
    group_service = group_ws_service.group_service
    group_id = str(uuid4())
    user_id = str(uuid4())
    sender_id = str(uuid4())
    message = SimpleNamespace(
        group_id=group_id,
        sender_id=sender_id,
        id=uuid4(),
    )
    repository = AsyncMock()
    repository.get_message_by_id.return_value = message
    monkeypatch.setattr(group_service, "message_repo", repository)
    members = AsyncMock()
    members.get_member.return_value = SimpleNamespace(is_active=True)
    monkeypatch.setattr(group_service, "member_repo", members)

    db = AsyncMock()
    result = await group_service.delete_message(
        db=db,
        group_id=group_id,
        message_id=str(message.id),
        user_id=user_id,
        delete_for="me",
    )

    repository.delete_for_user.assert_awaited_once_with(db, str(message.id), user_id)
    repository.delete_for_everyone.assert_not_awaited()
    assert result["data"]["deleted_for"] == [user_id]
    db.commit.assert_awaited_once()
