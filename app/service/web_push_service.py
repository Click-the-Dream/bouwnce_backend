from __future__ import annotations

import asyncio
import base64
import json
from typing import Any
from urllib.parse import urlparse

from cryptography.hazmat.primitives import serialization
from pywebpush import WebPushException, webpush
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.logger import log_internal_error
from app.models.web_push_subscription import WebPushSubscription
from app.schemas.web_push import WebPushSubscriptionIn
from app.utils.exception import BadRequestException

# Push services reply 404/410 when a subscription is stale (uninstalled,
# permission revoked, or expired). These subscriptions must be pruned.
_STALE_PUSH_STATUS_CODES = {404, 410}
_PUSH_TIMEOUT_SECONDS = 10.0


def _application_server_key(private_key_pem: str) -> str | None:
    """Derive the base64url application server key from the VAPID private key.

    This is the format `PushManager.subscribe()` expects for
    `applicationServerKey` (65-byte uncompressed EC point, base64url).
    """
    try:
        private_key = serialization.load_pem_private_key(
            private_key_pem.encode(), password=None
        )
        public_bytes = private_key.public_key().public_bytes(
            serialization.Encoding.X962,
            serialization.PublicFormat.UncompressedPoint,
        )
    except Exception:
        return None
    return base64.urlsafe_b64encode(public_bytes).rstrip(b"=").decode()


class WebPushService:
    @property
    def enabled(self) -> bool:
        """Web push is usable only when a VAPID private key and subject are set."""
        return bool(settings.VAPID_PRIVATE_KEY and settings.VAPID_SUBJECT)

    def public_key(self) -> str | None:
        """Application server key for the frontend, or None when disabled/misconfigured."""
        if not settings.VAPID_PRIVATE_KEY:
            return None
        return _application_server_key(settings.VAPID_PRIVATE_KEY)

    def _vapid_claims(self) -> dict[str, str]:
        return {"sub": settings.VAPID_SUBJECT}

    async def subscribe(
        self,
        db: AsyncSession,
        *,
        user_id: str,
        subscription: WebPushSubscriptionIn,
        user_agent: str | None = None,
    ) -> WebPushSubscription:
        self._validate_endpoint(subscription.endpoint)
        return await WebPushSubscription.upsert(
            db=db,
            user_id=user_id,
            endpoint=subscription.endpoint,
            p256dh=subscription.keys.p256dh,
            auth=subscription.keys.auth,
            expiration_time=subscription.expiration_time,
            user_agent=user_agent,
        )

    async def unsubscribe(
        self, db: AsyncSession, *, user_id: str, endpoint: str
    ) -> bool:
        return await WebPushSubscription.delete_for_user(
            db=db, user_id=user_id, endpoint=endpoint
        )

    @staticmethod
    def _validate_endpoint(endpoint: str) -> None:
        """Reject endpoints that are not https URLs.

        The Celery worker later POSTs push payloads to the stored endpoint, so an
        unvalidated endpoint would let an authenticated user weaponize the worker
        as an SSRF proxy against internal http:// hosts. Real browser push
        endpoints are always https.
        """
        parsed = urlparse(endpoint)
        if parsed.scheme != "https" or not parsed.netloc:
            raise BadRequestException("Invalid push endpoint: must be an https:// URL")

    async def send_to_user(
        self,
        db: AsyncSession,
        *,
        user_id: str,
        title: str,
        body: str,
        data: dict[str, Any],
    ) -> dict[str, Any]:
        """Send a web push to every browser subscription of a user.

        Returns ``{"sent", "removed", "skipped"}``. Subscriptions that the push
        service reports as stale (404/410) are deleted. Any other failure is
        treated as transient and leaves the subscription in place for the next
        attempt.
        """
        if not self.enabled:
            return {"sent": 0, "removed": 0, "skipped": True}

        subscriptions = await WebPushSubscription.list_for_user(db=db, user_id=user_id)
        if not subscriptions:
            return {"sent": 0, "removed": 0, "skipped": False}

        payload = json.dumps({"title": title, "body": body, "data": data})
        sent = 0
        removed = 0
        for subscription in subscriptions:
            try:
                await asyncio.to_thread(
                    webpush,
                    subscription_info={
                        "endpoint": subscription.endpoint,
                        "keys": {
                            "p256dh": subscription.p256dh,
                            "auth": subscription.auth,
                        },
                    },
                    data=payload,
                    vapid_private_key=settings.VAPID_PRIVATE_KEY,
                    vapid_claims=self._vapid_claims(),
                    timeout=_PUSH_TIMEOUT_SECONDS,
                )
                sent += 1
            except WebPushException as exc:
                status_code = (
                    getattr(exc.response, "status_code", None)
                    if exc.response is not None
                    else None
                )
                if status_code in _STALE_PUSH_STATUS_CODES:
                    await db.delete(subscription)
                    removed += 1
            except Exception as exc:
                # A failure on one subscription must never break the fan-out for
                # the user's other subscriptions, but unexpected errors must not
                # disappear silently either.
                log_internal_error(
                    exc=exc,
                    message="Unexpected error sending web push",
                    context={
                        "user_id": user_id,
                        "endpoint": subscription.endpoint,
                    },
                )
                continue
        return {"sent": sent, "removed": removed, "skipped": False}


web_push_service = WebPushService()
