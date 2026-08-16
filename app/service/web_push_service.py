from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any

from pywebpush import WebPushException, webpush

from app.core.config import settings
from app.models.web_push_subscription import WebPushSubscription

PUSH_TTL_SECONDS = 3600


def get_vapid_public_key() -> str:
    return settings.VAPID_PUBLIC_KEY


def _vapid_claims() -> dict[str, str]:
    subject = (settings.VAPID_SUBJECT or "").strip()
    if not subject:
        subject = f"mailto:{settings.BOUWNCE_SYSTEM_EMAIL}"
    return {"sub": subject}


def subscription_is_expired(subscription: WebPushSubscription) -> bool:
    """True when the browser-declared expiration time is in the past."""
    from datetime import UTC, datetime

    if subscription.expiration_time is None:
        return False
    return subscription.expiration_time <= datetime.now(UTC)


@dataclass
class DeliveryOutcome:
    """Result of delivering one notification to one subscription."""

    delivered: bool = False
    expired: bool = False  # 404/410 -> subscription no longer valid, remove it
    retry: bool = False  # 429/5xx -> requeue for a later attempt
    error: str | None = None


def send_web_push(
    subscription: WebPushSubscription,
    *,
    title: str,
    body: str,
    data: dict[str, Any] | None = None,
    ttl: int = PUSH_TTL_SECONDS,
) -> DeliveryOutcome:
    """Send an encrypted Web Push message to one browser subscription.

    Uses AES-128-GCM payload encryption + VAPID signing (handled by pywebpush).
    """
    payload = json.dumps(
        {"title": title or "Notification", "body": body or "", "data": data or {}}
    )
    subscription_info = {
        "endpoint": subscription.endpoint,
        "keys": {"p256dh": subscription.p256dh, "auth": subscription.auth},
    }
    try:
        webpush(
            subscription_info=subscription_info,
            data=payload,
            vapid_private_key=settings.VAPID_PRIVATE_KEY,
            vapid_claims=_vapid_claims(),
            ttl=ttl,
            timeout=10,
        )
        return DeliveryOutcome(delivered=True)
    except WebPushException as exc:
        status_code = exc.response.status_code if exc.response is not None else None
        if status_code in (404, 410):
            # Push service says this subscription is gone (user unsubscribed,
            # revoked permission, or the endpoint expired).
            return DeliveryOutcome(delivered=False, expired=True, error=str(exc))
        if status_code in (429, 500, 502, 503, 504):
            # Transient: push service is rate-limiting or having issues.
            return DeliveryOutcome(delivered=False, retry=True, error=str(exc))
        return DeliveryOutcome(delivered=False, error=str(exc))
    except Exception as exc:  # noqa: BLE001 - capture any send failure
        # e.g. malformed keys, network errors, VAPID config missing
        return DeliveryOutcome(delivered=False, error=str(exc))
