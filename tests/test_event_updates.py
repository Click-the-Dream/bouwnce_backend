from datetime import datetime
from unittest.mock import AsyncMock

import pytest

from app.event_broadcast.models.events import EventState, LocationType, OutingEvent
from app.event_broadcast.services.events import EventService


class Event:
    def __init__(self) -> None:
        self.id = "event-id"
        self.creator_id = "creator-id"
        self.name = "Original name"
        self.desc = "Original description"
        self.date = datetime(2026, 1, 1, 12, 0)
        self.location = "Lagos"
        self.location_type = LocationType.PHYSICAL
        self.link = None
        self.banner_url = "https://example.test/banner.png"
        self.state = EventState.DRAFT
        self.ticket_info = None
        self.interests = None

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "creator_id": self.creator_id,
            "name": self.name,
            "desc": self.desc,
            "date": self.date.isoformat(),
            "location": self.location,
            "location_type": self.location_type.value,
            "link": self.link,
            "banner_url": self.banner_url,
            "state": self.state.value,
            "ticket_info": self.ticket_info,
            "interests": self.interests,
        }


class User:
    id = "creator-id"


@pytest.mark.asyncio
async def test_event_update_converts_an_iso_date_to_datetime(monkeypatch):
    event = Event()
    db = AsyncMock()
    captured = {}

    async def update_event(_db, _event_id, update_data):
        captured.update(update_data)
        for key, value in update_data.items():
            setattr(event, key, value)
        return event

    monkeypatch.setattr(OutingEvent, "get_event_by_id", AsyncMock(return_value=event))
    monkeypatch.setattr(OutingEvent, "update_event", update_event)

    await EventService().update_event(
        db=db,
        current_user=User(),
        event_id="fd7f3eb1-b023-4caa-a50d-3e611f0e548e",
        update_data={"date": "2026-12-31T20:00:00"},
    )

    assert captured["date"] == datetime(2026, 12, 31, 20, 0)
    db.commit.assert_awaited_once()


@pytest.mark.asyncio
async def test_event_update_normalizes_a_cleared_link_to_null(monkeypatch):
    event = Event()
    db = AsyncMock()
    captured = {}

    async def update_event(_db, _event_id, update_data):
        captured.update(update_data)
        return event

    monkeypatch.setattr(OutingEvent, "get_event_by_id", AsyncMock(return_value=event))
    monkeypatch.setattr(OutingEvent, "update_event", update_event)

    await EventService().update_event(
        db=db,
        current_user=User(),
        event_id="fd7f3eb1-b023-4caa-a50d-3e611f0e548e",
        update_data={"link": "  "},
    )

    assert captured["link"] is None
