import asyncio
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import pytest
from pywebpush import WebPushException

from app.schemas.web_push import WebPushSubscriptionIn, WebPushSubscriptionKeys
from app.service.web_push_service import WebPushService, web_push_service
from app.utils.exception import BadRequestException


class _FakeDB:
    """Minimal stand-in for AsyncSession: records deleted objects."""

    def __init__(self) -> None:
        self.deleted: list[object] = []

    async def delete(self, obj: object) -> None:
        self.deleted.append(obj)


def _subscription(
    *, endpoint: str = "https://push.example/endpoint-1"
) -> SimpleNamespace:
    return SimpleNamespace(
        endpoint=endpoint,
        p256dh="p256dh-key",
        auth="auth-secret",
    )


def _run(coro) -> dict:
    return asyncio.run(coro)


def test_subscribe_rejects_non_https_endpoint() -> None:
    bad = WebPushSubscriptionIn(
        endpoint="http://169.254.169.254/latest/meta-data/",
        keys=WebPushSubscriptionKeys(p256dh="p256dh-key", auth="auth-secret"),
    )
    with pytest.raises(BadRequestException):
        _run(
            web_push_service.subscribe(db=_FakeDB(), user_id="user-1", subscription=bad)
        )


def test_send_to_user_skips_when_disabled() -> None:
    with patch.object(WebPushService, "enabled", new=False):
        result = _run(
            web_push_service.send_to_user(
                db=_FakeDB(), user_id="user-1", title="t", body="b", data={}
            )
        )

    assert result == {"sent": 0, "removed": 0, "skipped": True}


def test_send_to_user_returns_early_when_no_subscriptions() -> None:
    with (
        patch.object(WebPushService, "enabled", new=True),
        patch(
            "app.service.web_push_service.WebPushSubscription.list_for_user",
            new_callable=AsyncMock,
            return_value=[],
        ) as list_for_user,
    ):
        result = _run(
            web_push_service.send_to_user(
                db=_FakeDB(), user_id="user-1", title="t", body="b", data={}
            )
        )

    list_for_user.assert_awaited_once()
    assert result == {"sent": 0, "removed": 0, "skipped": False}


def test_send_to_user_prunes_stale_subscription() -> None:
    stale = _subscription(endpoint="https://push.example/stale")
    good = _subscription(endpoint="https://push.example/good")

    def _fake_webpush(*, subscription_info: dict, **_kwargs) -> None:
        if subscription_info["endpoint"] == stale.endpoint:
            raise WebPushException("gone", response=SimpleNamespace(status_code=410))

    db = _FakeDB()
    with (
        patch.object(WebPushService, "enabled", new=True),
        patch(
            "app.service.web_push_service.WebPushSubscription.list_for_user",
            new_callable=AsyncMock,
            return_value=[stale, good],
        ),
        patch("app.service.web_push_service.webpush", side_effect=_fake_webpush),
    ):
        result = _run(
            web_push_service.send_to_user(
                db=db, user_id="user-1", title="t", body="b", data={}
            )
        )

    assert result == {"sent": 1, "removed": 1, "skipped": False}
    assert db.deleted == [stale]


def test_send_to_user_keeps_subscription_on_transient_error() -> None:
    sub = _subscription()
    db = _FakeDB()

    def _fake_webpush(*, subscription_info: dict, **_kwargs) -> None:
        raise WebPushException(
            "too many requests", response=SimpleNamespace(status_code=429)
        )

    with (
        patch.object(WebPushService, "enabled", new=True),
        patch(
            "app.service.web_push_service.WebPushSubscription.list_for_user",
            new_callable=AsyncMock,
            return_value=[sub],
        ),
        patch("app.service.web_push_service.webpush", side_effect=_fake_webpush),
    ):
        result = _run(
            web_push_service.send_to_user(
                db=db, user_id="user-1", title="t", body="b", data={}
            )
        )

    assert result == {"sent": 0, "removed": 0, "skipped": False}
    assert db.deleted == []
