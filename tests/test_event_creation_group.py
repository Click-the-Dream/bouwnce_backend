from datetime import datetime, timedelta
from types import SimpleNamespace
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest

from app.event_broadcast.models.events import OutingEvent
from app.event_broadcast.schemas.events import CreateEventSchema
from app.event_broadcast.services.events import EventService


@pytest.mark.asyncio
async def test_create_event_can_create_group_in_same_flow(monkeypatch):
    event_id = uuid4()
    creator_id = uuid4()
    group_id = str(uuid4())
    event = SimpleNamespace(
        id=event_id,
        creator_id=creator_id,
        name="Community meetup",
        state="draft",
        location_type="physical",
        to_dict=lambda: {
            "id": event_id,
            "creator_id": creator_id,
            "name": "Community meetup",
            "desc": "Meetup",
            "date": "2027-01-01T12:00:00",
            "location": "Lagos",
            "location_type": "physical",
            "link": None,
            "banner_url": "https://example.com/banner.png",
            "state": "draft",
            "ticket_info": None,
            "interests": None,
            "created_at": "2026-10-16T12:00:00",
            "updated_at": "2026-10-16T12:00:00",
        },
    )
    db = AsyncMock()
    current_user = SimpleNamespace(id=creator_id)
    create_event = AsyncMock(return_value=event)
    create_group = AsyncMock(
        return_value={"data": {"group": {"id": group_id}}}
    )
    monkeypatch.setattr(OutingEvent, "create_event", create_event)
    monkeypatch.setattr(
        "app.event_broadcast.services.events.event_group_service.create_or_get_for_host",
        create_group,
    )

    payload = CreateEventSchema(
        name="Community meetup",
        desc="Meetup",
        date=(datetime.now() + timedelta(days=1)).isoformat(),
        location="Lagos",
        location_type="physical",
        banner_url="https://example.com/banner.png",
        state="draft",
        create_group=True,
    )
    result = await EventService().create_event(
        db=db,
        current_user=current_user,
        event_data=payload.model_dump(),
    )

    create_event.assert_awaited_once()
    assert "create_group" not in create_event.await_args.args[1]
    create_group.assert_awaited_once_with(
        db=db,
        event_id=str(event_id),
        host_id=str(creator_id),
    )
    db.commit.assert_awaited_once()
    assert result["data"]["group_id"] == group_id


@pytest.mark.asyncio
async def test_create_event_does_not_create_group_by_default(monkeypatch):
    event_id = uuid4()
    creator_id = uuid4()
    event = SimpleNamespace(
        id=event_id,
        creator_id=creator_id,
        name="Community meetup",
        state="draft",
        location_type="physical",
        to_dict=lambda: {
            "id": event_id,
            "creator_id": creator_id,
            "name": "Community meetup",
            "desc": "Meetup",
            "date": "2027-01-01T12:00:00",
            "location": "Lagos",
            "location_type": "physical",
            "link": None,
            "banner_url": "https://example.com/banner.png",
            "state": "draft",
            "ticket_info": None,
            "interests": None,
            "created_at": "2026-10-16T12:00:00",
            "updated_at": "2026-10-16T12:00:00",
        },
    )
    db = AsyncMock()
    monkeypatch.setattr(
        OutingEvent, "create_event", AsyncMock(return_value=event)
    )
    create_group = AsyncMock()
    monkeypatch.setattr(
        "app.event_broadcast.services.events.event_group_service.create_or_get_for_host",
        create_group,
    )

    payload = CreateEventSchema(
        name="Community meetup",
        desc="Meetup",
        date=(datetime.now() + timedelta(days=1)).isoformat(),
        location="Lagos",
        location_type="physical",
        banner_url="https://example.com/banner.png",
        state="draft",
    )
    result = await EventService().create_event(
        db=db,
        current_user=SimpleNamespace(id=creator_id),
        event_data=payload.model_dump(),
    )

    create_group.assert_not_awaited()
    assert result["data"]["group_id"] is None
