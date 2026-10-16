from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock
from uuid import uuid4

import pytest
from sqlalchemy.dialects import postgresql

from app.event_broadcast.services.event_group import EventGroupService
from app.utils.exception import ForbiddenException


class FakeResult:
    def __init__(self, *, scalar=None, one=None):
        self._scalar = scalar
        self._one = one

    def scalar_one_or_none(self):
        return self._scalar

    def scalar_one(self):
        return self._scalar

    def one_or_none(self):
        return self._one


@pytest.mark.asyncio
async def test_create_event_group_is_idempotent_and_backfills(monkeypatch):
    event_id = uuid4()
    host_id = str(uuid4())
    group_id = uuid4()
    event = SimpleNamespace(
        id=event_id,
        creator_id=host_id,
        name="Community meetup",
    )
    group = SimpleNamespace(
        id=group_id,
        to_dict=lambda: {"id": str(group_id), "name": "Event group"},
    )
    link = SimpleNamespace(group_id=group_id, created_by=host_id)
    db = AsyncMock()
    db.add = Mock()
    db.execute.side_effect = [
        FakeResult(scalar=event),
        FakeResult(scalar=link),
        FakeResult(scalar=group),
        FakeResult(scalar=8),
    ]
    backfill = AsyncMock()
    add_membership = AsyncMock()
    monkeypatch.setattr(EventGroupService, "_backfill_confirmed_attendees", backfill)
    monkeypatch.setattr(EventGroupService, "_add_membership", add_membership)

    result = await EventGroupService.create_or_get_for_host(
        db=db, event_id=str(event_id), host_id=host_id
    )

    assert result["status_code"] == 200
    assert result["data"]["member_count"] == 8
    assert result["data"]["group"]["id"] == str(group_id)
    add_membership.assert_awaited_once_with(
        db,
        group_id=str(group_id),
        user_id=host_id,
        invited_by=host_id,
        role="owner",
    )
    db.add.assert_not_called()
    backfill.assert_awaited_once_with(
        db,
        event_id=str(event_id),
        group_id=str(group_id),
        host_id=host_id,
    )


@pytest.mark.asyncio
async def test_first_group_creation_backfills_and_announces_once(monkeypatch):
    event_id = uuid4()
    host_id = str(uuid4())
    group_id = uuid4()
    event = SimpleNamespace(
        id=event_id,
        creator_id=host_id,
        name="Community meetup",
    )
    group = SimpleNamespace(
        id=group_id,
        to_dict=lambda: {"id": str(group_id), "name": "Event group"},
    )
    db = AsyncMock()
    db.add = Mock()
    db.execute.side_effect = [
        FakeResult(scalar=event),
        FakeResult(scalar=None),
        FakeResult(scalar=group),
        FakeResult(scalar=4),
    ]
    add_membership = AsyncMock()
    backfill = AsyncMock()
    notify = AsyncMock()
    monkeypatch.setattr(EventGroupService, "_add_membership", add_membership)
    monkeypatch.setattr(EventGroupService, "_backfill_confirmed_attendees", backfill)
    monkeypatch.setattr(EventGroupService, "_notify_confirmed_attendees", notify)

    result = await EventGroupService.create_or_get_for_host(
        db=db, event_id=str(event_id), host_id=host_id
    )

    assert result["status_code"] == 201
    db.add.assert_called_once()
    db.flush.assert_awaited_once()
    backfill.assert_awaited_once()
    notify.assert_awaited_once_with(
        db,
        event=event,
        group_id=str(group_id),
        host_id=host_id,
    )


@pytest.mark.asyncio
async def test_create_event_group_requires_host():
    event = SimpleNamespace(id=uuid4(), creator_id=str(uuid4()), name="Meetup")
    db = AsyncMock()
    db.execute.return_value = FakeResult(scalar=event)

    with pytest.raises(ForbiddenException):
        await EventGroupService.create_or_get_for_host(
            db=db, event_id=str(event.id), host_id=str(uuid4())
        )

    db.execute.assert_awaited_once()
    db.add.assert_not_called()


@pytest.mark.asyncio
async def test_backfill_uses_idempotent_set_based_insert():
    db = AsyncMock()

    await EventGroupService._backfill_confirmed_attendees(
        db,
        event_id=str(uuid4()),
        group_id=str(uuid4()),
        host_id=str(uuid4()),
    )

    statement = db.execute.await_args.args[0]
    compiled = str(statement.compile(dialect=postgresql.dialect()))
    assert "INSERT INTO group_members" in compiled
    assert "SELECT DISTINCT" in compiled
    assert "ON CONFLICT (group_id, user_id) DO UPDATE" in compiled
    assert "payment_status" in compiled
    assert "attendance_status" in compiled
    assert "is_deleted IS false" in compiled
    assert "gen_random_uuid()" in compiled


@pytest.mark.asyncio
async def test_group_created_notifications_are_inserted_setwise():
    event = SimpleNamespace(id=uuid4(), name="Meetup")
    db = AsyncMock()

    await EventGroupService._notify_confirmed_attendees(
        db,
        event=event,
        group_id=str(uuid4()),
        host_id=str(uuid4()),
    )

    compiled = str(db.execute.await_args.args[0].compile(dialect=postgresql.dialect()))
    assert "INSERT INTO notifications" in compiled
    assert "SELECT DISTINCT" in compiled
    assert "jsonb_build_object" in compiled
    assert "gen_random_uuid()" in compiled


@pytest.mark.asyncio
async def test_confirmed_attendee_is_added_only_when_event_group_exists(monkeypatch):
    link = SimpleNamespace(group_id=str(uuid4()), created_by=str(uuid4()))
    user_id = str(uuid4())
    db = AsyncMock()
    db.execute.return_value = FakeResult(scalar=link)
    add_membership = AsyncMock()
    monkeypatch.setattr(EventGroupService, "_add_membership", add_membership)

    await EventGroupService.add_confirmed_attendee(
        db=db, event_id=str(uuid4()), user_id=user_id
    )

    add_membership.assert_awaited_once_with(
        db,
        group_id=link.group_id,
        user_id=user_id,
        invited_by=link.created_by,
    )


@pytest.mark.asyncio
async def test_confirmed_attendee_hook_is_noop_without_event_group(monkeypatch):
    db = AsyncMock()
    db.execute.return_value = FakeResult(scalar=None)
    add_membership = AsyncMock()
    monkeypatch.setattr(EventGroupService, "_add_membership", add_membership)

    await EventGroupService.add_confirmed_attendee(
        db=db, event_id=str(uuid4()), user_id=str(uuid4())
    )

    add_membership.assert_not_awaited()
