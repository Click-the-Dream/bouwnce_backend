from __future__ import annotations

from datetime import UTC, datetime
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
from app.matching_ground.model.user_block import UserBlock
from app.matching_ground.service.matching.match_lifecycle import MatchLifecycleService
from app.models.user import User


def test_connection_status_endpoint_is_registered() -> None:
    assert any(
        route.path.endswith("/matches/connection-status/{other_user_id}")
        for route in main.app.routes
    )


@pytest.mark.asyncio
async def test_get_connection_status_reports_an_active_connection(monkeypatch) -> None:
    user_id = uuid4()
    other_user_id = uuid4()
    accepted_at = datetime(2026, 10, 14, 12, tzinfo=UTC)
    match = SimpleNamespace(accepted_at=accepted_at)

    monkeypatch.setattr(User, "get_by_id", AsyncMock(return_value=object()))
    monkeypatch.setattr(
        Match, "find_active_between_any_direction", AsyncMock(return_value=match)
    )
    monkeypatch.setattr(
        MatchRequest, "find_latest_between_any_direction", AsyncMock(return_value=None)
    )

    result = await MatchLifecycleService().get_connection_status(
        session=object(),
        user_id=user_id,
        other_user_id=other_user_id,
    )

    assert result == {
        "other_user_id": str(other_user_id),
        "status": "connected",
        "is_connected": True,
        "request_id": None,
        "request_direction": None,
        "requested_at": None,
        "responded_at": None,
        "connected_at": accepted_at.isoformat(),
    }


@pytest.mark.asyncio
async def test_get_connection_status_reports_incoming_request_state(
    monkeypatch,
) -> None:
    user_id = uuid4()
    other_user_id = uuid4()
    request = SimpleNamespace(
        id=uuid4(),
        requester_id=other_user_id,
        status="pending",
        created_at=SimpleNamespace(isoformat=lambda: "requested"),
        responded_at=None,
    )

    monkeypatch.setattr(User, "get_by_id", AsyncMock(return_value=object()))
    monkeypatch.setattr(
        Match, "find_active_between_any_direction", AsyncMock(return_value=None)
    )
    monkeypatch.setattr(
        MatchRequest,
        "find_latest_between_any_direction",
        AsyncMock(return_value=request),
    )

    result = await MatchLifecycleService().get_connection_status(
        session=object(),
        user_id=user_id,
        other_user_id=other_user_id,
    )

    assert result["status"] == "pending"
    assert result["is_connected"] is False
    assert result["request_id"] == str(request.id)
    assert result["request_direction"] == "incoming"
    assert result["requested_at"] == "requested"


@pytest.mark.asyncio
async def test_create_request_does_not_resend_a_rejected_request(monkeypatch) -> None:
    user_id = uuid4()
    other_user_id = uuid4()
    rejected_request = SimpleNamespace(id=uuid4(), status="rejected")
    create_pending = AsyncMock()

    monkeypatch.setattr(UserBlock, "is_blocked_between", AsyncMock(return_value=False))
    monkeypatch.setattr(
        MatchRequest,
        "find_latest_between_any_direction",
        AsyncMock(return_value=rejected_request),
    )
    monkeypatch.setattr(MatchRequest, "create_pending", create_pending)

    result = await MatchLifecycleService().create_request(
        session=cast(AsyncSession, object()),
        requester=cast(
            User, SimpleNamespace(id=user_id, username="requester", full_name=None)
        ),
        target_user_id=other_user_id,
        note=None,
        background_tasks=BackgroundTasks(),
        redis=cast(Redis, object()),
    )

    assert result == {
        "status": "rejected",
        "request_id": str(rejected_request.id),
    }
    create_pending.assert_not_awaited()
