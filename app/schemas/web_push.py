from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


class WebPushSubscriptionKeys(BaseModel):
    """The `keys` object of a browser PushSubscription."""

    p256dh: str = Field(..., min_length=1, max_length=256)
    auth: str = Field(..., min_length=1, max_length=128)


class WebPushSubscriptionIn(BaseModel):
    """Body of `POST /api/v1/web-push/subscriptions` — the browser PushSubscription JSON."""

    endpoint: str = Field(..., min_length=1, max_length=512)
    keys: WebPushSubscriptionKeys
    expiration_time: datetime | None = None


class WebPushUnsubscribeIn(BaseModel):
    """Body of `DELETE /api/v1/web-push/subscriptions`."""

    endpoint: str = Field(..., min_length=1, max_length=512)


class WebPushPublicKeyOut(BaseModel):
    """VAPID application server key for `PushManager.subscribe({ applicationServerKey })`."""

    enabled: bool
    public_key: str | None = None
