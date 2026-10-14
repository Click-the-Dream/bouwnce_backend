from __future__ import annotations

from datetime import UTC, datetime, timedelta
from types import SimpleNamespace
from typing import cast
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest
from fastapi import BackgroundTasks
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

import main
from app.matching_ground.model.match import Match, MatchRequest
from app.matching_ground.model.notification import Notification
from app.matching_ground.model.user_block import UserBlock
from app.matching_ground.service.matching import match_lifecycle
from app.matching_ground.service.matching.match_lifecycle import MatchLifecycleService
from app.models.chat import Conversation
from app.models.user import User
from app.worker.event_system import EventNames, PushNotificationEvent


def test_match_request_endpoints_are_registered() -> None:
    assert any(route.path.endswith("/matches/requests") for route in main.app.routes)


@pytest.mark.asyncio
async def test_new_match_request_is_queued_as_push(monkeypatch) -> None:
    requester_id = uuid4()
    target_id = uuid4()
    request = SimpleNamespace(id=uuid4())
    requester = SimpleNamespace(
        id=requester_id,
        username="requester",
        full_name="Requester",
        profile_pic={"url": "https://images.example/requester.png"},
    )
    target_user = SimpleNamespace(email="target@example.com")
    dispatch = AsyncMock()

    monkeypatch.setattr(UserBlock, "is_blocked_between", AsyncMock(return_value=False))
    monkeypatch.setattr(
        MatchRequest, "find_latest_between_any_direction", AsyncMock(return_value=None)
    )
    monkeypatch.setattr(
        Match, "find_active_between_any_direction", AsyncMock(return_value=None)
    )
    monkeypatch.setattr(User, "get_by_id", AsyncMock(return_value=target_user))
    monkeypatch.setattr(MatchRequest, "create_pending", AsyncMock(return_value=request))
    monkeypatch.setattr(Notification, "create", AsyncMock())
    monkeypatch.setattr(match_lifecycle, "dispatch_event", dispatch)
    monkeypatch.setattr(
        match_lifecycle,
        "generate_email_content",
        lambda **_: SimpleNamespace(subject="request", html_content="email"),
    )

    await MatchLifecycleService().create_request(
        session=cast(AsyncSession, object()),
        requester=cast(User, requester),
        target_user_id=target_id,
        note=None,
        background_tasks=BackgroundTasks(),
        redis=cast(Redis, object()),
    )

    dispatch.assert_awaited_once()
    args = dispatch.await_args.args
    push = args[1]
    assert args[0] == EventNames.PUSH_NOTIFICATION
    assert isinstance(push, PushNotificationEvent)
    assert push.user_id == str(target_id)
    assert push.data["type"] == "match.request.created"
    assert push.data["request_id"] == str(request.id)
    assert push.data["sender_profile_image"] == requester.profile_pic


@pytest.mark.asyncio
async def test_accepted_match_request_is_queued_as_push(monkeypatch) -> None:
    requester_id = uuid4()
    target_id = uuid4()
    request = SimpleNamespace(
        id=uuid4(),
        requester_id=requester_id,
        target_user_id=target_id,
        status="pending",
        expires_at=datetime.now(UTC) + timedelta(days=1),
        responded_at=None,
        set_status=AsyncMock(),
    )
    match = SimpleNamespace(id=uuid4())
    conversation = SimpleNamespace(id=uuid4())
    target_user = SimpleNamespace(
        id=target_id,
        username="target",
        full_name="Target",
        profile_pic={"url": "https://images.example/target.png"},
    )
    dispatch = AsyncMock()
    session = cast(AsyncSession, object())

    monkeypatch.setattr(MatchRequest, "get_by_id", AsyncMock(return_value=request))
    monkeypatch.setattr(Match, "create_accepted", AsyncMock(return_value=match))
    monkeypatch.setattr(
        Conversation, "get_or_create_between", AsyncMock(return_value=conversation)
    )
    monkeypatch.setattr(User, "get_by_id", AsyncMock(return_value=target_user))
    monkeypatch.setattr(Notification, "create", AsyncMock())
    monkeypatch.setattr(match_lifecycle, "dispatch_event", dispatch)

    await MatchLifecycleService().respond_request(
        session=session,
        request_id=request.id,
        responder_user_id=target_id,
        accepted=True,
        redis=cast(Redis, object()),
    )

    request.set_status.assert_awaited_once_with(session, "accepted")
    dispatch.assert_awaited_once()
    args = dispatch.await_args.args
    push = args[1]
    assert args[0] == EventNames.PUSH_NOTIFICATION
    assert isinstance(push, PushNotificationEvent)
    assert push.user_id == str(requester_id)
    assert push.data["type"] == "match.request.accepted"
    assert push.data["request_id"] == str(request.id)
    assert push.data["conversation_id"] == str(conversation.id)
