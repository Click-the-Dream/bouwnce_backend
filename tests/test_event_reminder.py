"""Unit tests for the event reminder job.

No live DB/Redis/Celery: the fake-session pattern from test_web_push.py plus
pure-function tests for the due-window logic.
"""

import asyncio
from datetime import UTC, datetime, timedelta
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

from app.core.config import settings
from app.event_broadcast.models.events import EventState
from app.event_broadcast.services.reminder import (
    due_windows,
    parse_reminder_windows,
    reminder_content,
)
from app.worker.tasks.event_reminder import (
    _claim_due_windows,
    _dispatch,
    _release_claims,
    send_event_reminders,
)

NOW = datetime(2026, 10, 14, 12, 0, tzinfo=UTC)


# ---------------------------------------------------------------------------
# Pure logic: window parsing + due decision
# ---------------------------------------------------------------------------


class TestParseReminderWindows:
    def test_parses_the_documented_default(self) -> None:
        assert parse_reminder_windows("7,3,2,1") == [7, 3, 2, 1]

    def test_sorts_descending_and_dedupes(self) -> None:
        assert parse_reminder_windows("1,7,3,7,2") == [7, 3, 2, 1]

    def test_skips_empty_and_invalid_segments(self) -> None:
        assert parse_reminder_windows(" 7 , abc, , 3, -4, 0") == [7, 3]

    def test_empty_string_yields_no_windows(self) -> None:
        assert parse_reminder_windows("") == []


class TestDueWindows:
    def test_only_the_lead_window_is_due_at_lead_time(self) -> None:
        # Event is exactly 7 days out: only the 7-day window's target time
        # (now itself) has arrived.
        event_date = NOW + timedelta(days=7)
        assert due_windows(event_date, NOW, [7, 3, 2, 1]) == [7]

    def test_all_windows_due_when_event_is_tomorrow(self) -> None:
        # A 7-day-out event's smaller windows past-fired already.
        event_date = NOW + timedelta(days=1)
        assert due_windows(event_date, NOW, [7, 3, 2, 1]) == [7, 3, 2, 1]

    def test_future_window_not_due(self) -> None:
        event_date = NOW + timedelta(days=2)
        assert due_windows(event_date, NOW, [1]) == []

    def test_started_event_never_due(self) -> None:
        assert due_windows(NOW - timedelta(seconds=1), NOW, [7, 1]) == []

    def test_defaults_to_configured_windows(self) -> None:
        event_date = NOW + timedelta(days=7)
        assert due_windows(event_date, NOW) == [7]


class TestReminderContent:
    def _event(self) -> SimpleNamespace:
        return SimpleNamespace(name="Summer Bash", location="Lekki Phase 1")

    def test_plural_days(self) -> None:
        content = reminder_content(self._event(), 3)
        assert content.title == "Summer Bash starts in 3 days"
        assert "Summer Bash" in content.email_subject
        assert "Lekki Phase 1" in content.body

    def test_singular_day(self) -> None:
        content = reminder_content(self._event(), 1)
        assert content.title == "Summer Bash starts in 1 day"


# ---------------------------------------------------------------------------
# Candidate selection against a fake session
# ---------------------------------------------------------------------------


class _FakeResult:
    def __init__(self, rows):
        self._rows = rows

    def all(self):
        return self._rows


class _FakeSession:
    """Records execute calls and replays canned results in order."""

    def __init__(self, results):
        self._results = list(results)
        self.statements = []

    async def execute(self, statement):
        self.statements.append(statement)
        # Any execute beyond the canned results just returns an empty result
        # (fire-and-forget statements like UPDATE/DELETE).
        return self._results.pop(0) if self._results else _FakeResult([])

    async def commit(self):
        pass


def _candidate_event(days_away: int) -> SimpleNamespace:
    return SimpleNamespace(
        id="22222222-2222-2222-2222-222222222222",
        name="Summer Bash",
        date=NOW + timedelta(days=days_away),
        location="Lekki Phase 1",
        location_type="physical",
        banner_url="https://cdn.example.com/banner.jpg",
        state=EventState.LIVE,
    )


def _attendance() -> SimpleNamespace:
    return SimpleNamespace(
        id="33333333-3333-3333-3333-333333333333",
        user_id="44444444-4444-4444-4444-444444444444",
    )


class TestFindDueCandidates:
    def test_filters_out_already_sent_windows(self) -> None:
        from app.event_broadcast.services.reminder import find_due_reminder_candidates

        # 1 day out: every configured window is due.
        event = _candidate_event(days_away=1)
        attendance = _attendance()
        db = _FakeSession(
            [
                _FakeResult([(event, attendance)]),
                _FakeResult([(event.id, attendance.id, 7)]),
            ]
        )
        with patch.object(settings, "EVENT_REMINDER_ENABLED", True):
            candidates = asyncio.run(find_due_reminder_candidates(db, NOW))
        # Window 7 was already sent; only the remaining windows are fresh.
        assert len(candidates) == 1
        assert candidates[0].windows == [3, 2, 1]

    def test_returns_candidate_with_fresh_windows(self) -> None:
        from app.event_broadcast.services.reminder import find_due_reminder_candidates

        event = _candidate_event(days_away=7)
        attendance = _attendance()
        db = _FakeSession([_FakeResult([(event, attendance)]), _FakeResult([])])
        with patch.object(settings, "EVENT_REMINDER_ENABLED", True):
            candidates = asyncio.run(find_due_reminder_candidates(db, NOW))
        assert len(candidates) == 1
        assert candidates[0].windows == [7]

    def test_disabled_returns_nothing_without_hitting_the_db(self) -> None:
        from app.event_broadcast.services.reminder import find_due_reminder_candidates

        db = _FakeSession([])
        with patch.object(settings, "EVENT_REMINDER_ENABLED", False):
            assert asyncio.run(find_due_reminder_candidates(db, NOW)) == []
        assert db.statements == []


# ---------------------------------------------------------------------------
# Task orchestration with fakes
# ---------------------------------------------------------------------------


class _FakeSessionCtx:
    def __init__(self, session: _FakeSession):
        self._session = session

    async def __aenter__(self):
        return self._session

    async def __aexit__(self, *exc):
        return False


def _patched_session(session: _FakeSession):
    return patch(
        "app.worker.tasks.event_reminder.get_async_session",
        MagicMock(return_value=_FakeSessionCtx(session)),
    )


class TestClaimDueWindows:
    def test_maps_claim_rows_to_candidates(self) -> None:
        event = _candidate_event(days_away=10)
        attendance = _attendance()
        candidate = SimpleNamespace(event=event, attendance=attendance, windows=[7, 3])
        claim_rows = [SimpleNamespace(id="claim-1"), SimpleNamespace(id="claim-2")]

        with (
            patch(
                "app.worker.tasks.event_reminder.find_due_reminder_candidates",
                new=AsyncMock(return_value=[candidate]),
            ),
            _patched_session(_FakeSession([])),
            patch(
                "app.worker.tasks.event_reminder.EventReminderLog.claim_windows",
                new=AsyncMock(return_value=claim_rows),
            ),
        ):
            claimed = asyncio.run(_claim_due_windows())

        assert len(claimed) == 1
        assert claimed[0].claim_ids == ["claim-1", "claim-2"]


class TestDispatch:
    def _claimed(
        self, attendance: SimpleNamespace, claim_id: str
    ) -> SimpleNamespace:
        return SimpleNamespace(
            candidate=SimpleNamespace(
                event=_candidate_event(days_away=10),
                attendance=attendance,
                windows=[3, 2],
            ),
            claim_ids=[claim_id],
        )

    def test_dispatches_email_and_push_then_marks_sent(self) -> None:
        attendance = SimpleNamespace(
            user=SimpleNamespace(email="a@b.com", username="ada"),
            user_id="44444444-4444-4444-4444-444444444444",
        )
        claimed = self._claimed(attendance, "c1")
        db = _FakeSession([])

        with (
            _patched_session(db),
            patch(
                "app.worker.tasks.event_reminder.send_email_using_worker"
            ) as email_task,
            patch(
                "app.worker.tasks.event_reminder.dispatch_event", new=AsyncMock()
            ) as dispatch,
            patch.object(settings, "EVENT_REMINDER_MAX_EMAILS_PER_RUN", 5),
        ):
            emails = asyncio.run(_dispatch(MagicMock(), [claimed]))

        assert emails == 1
        # Email: queued on the Celery task with the reminder template, copy
        # built from the nearest due window (3 here).
        email_call = email_task.delay.call_args
        assert email_call.kwargs["email_to"] == "a@b.com"
        # Callers reference the COMPILED build artifact, matching every other
        # sender in the codebase (not the raw .mjml source).
        assert email_call.kwargs["template_name"] == "event_reminder.html"
        assert "3 days" in email_call.kwargs["subject"]
        # Push always went through the shared fan-out.
        assert dispatch.await_count == 1
        push_payload = dispatch.call_args.args[1]
        assert push_payload.data["type"] == "event.reminder"
        assert push_payload.data["days_before"] == 3
        # Claims marked sent in the same session.
        assert len(db.statements) == 1

    def test_email_cap_leaves_push_untouched(self) -> None:
        attendance = SimpleNamespace(
            user=SimpleNamespace(email="a@b.com", username="ada"),
            user_id="44444444-4444-4444-4444-444444444444",
        )
        claimed = [
            self._claimed(attendance, "c1"),
            self._claimed(attendance, "c2"),
        ]
        db = _FakeSession([])
        with (
            _patched_session(db),
            patch(
                "app.worker.tasks.event_reminder.send_email_using_worker"
            ) as email_task,
            patch(
                "app.worker.tasks.event_reminder.dispatch_event", new=AsyncMock()
            ) as dispatch,
            patch.object(settings, "EVENT_REMINDER_MAX_EMAILS_PER_RUN", 1),
        ):
            emails = asyncio.run(_dispatch(MagicMock(), claimed))

        assert emails == 1
        assert email_task.delay.call_count == 1
        # Both pushes went out despite the email cap.
        assert dispatch.await_count == 2


class TestReleaseClaims:
    def test_deletes_unsent_claims_only(self) -> None:
        db = _FakeSession([])
        with _patched_session(db):
            asyncio.run(_release_claims(["c1", "c2"]))
        assert len(db.statements) == 1

    def test_no_ids_is_noop(self) -> None:
        db = _FakeSession([])
        with _patched_session(db):
            asyncio.run(_release_claims([]))
        assert db.statements == []


# ---------------------------------------------------------------------------
# The production trigger: Celery beat wiring + task entry point
# ---------------------------------------------------------------------------


class TestBeatSchedule:
    def test_beat_schedule_wires_event_reminder(self) -> None:
        from app.worker.celery_app import celery_app

        schedule = celery_app.conf.beat_schedule
        assert "send-event-reminders" in schedule
        entry = schedule["send-event-reminders"]
        assert entry["task"] == "app.worker.tasks.event_reminder.send_event_reminders"
        assert entry["schedule"] == 900.0

    def test_task_registered_on_celery_app(self) -> None:
        from app.worker.celery_app import celery_app

        assert (
            celery_app.tasks.get("app.worker.tasks.event_reminder.send_event_reminders")
            is not None
        )

    def test_task_skipped_when_disabled(self) -> None:
        with patch.object(settings, "EVENT_REMINDER_ENABLED", False):
            assert send_event_reminders() == {"skipped": True}

    def test_task_survives_infra_failure(self) -> None:
        with (
            patch.object(settings, "EVENT_REMINDER_ENABLED", True),
            patch(
                "app.worker.tasks.event_reminder._run_cycle_with_redis",
                new=AsyncMock(side_effect=RuntimeError("redis down")),
            ),
        ):
            assert send_event_reminders() == {"error": "redis down"}


# ---------------------------------------------------------------------------
# Model-level dedup contract (no DB)
# ---------------------------------------------------------------------------


class TestClaimWindowsGuard:
    def test_empty_claims_is_noop(self) -> None:
        from app.event_broadcast.models.reminder import EventReminderLog

        db = _FakeSession([])
        assert asyncio.run(EventReminderLog.claim_windows(db, [])) == []
        assert db.statements == []
