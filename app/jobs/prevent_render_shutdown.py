import asyncio

import httpx

from app.core.config import settings
from app.core.logger import logger


async def call_health_endpoint_cron_task():
    if not settings.SELF_PING_ENABLED:
        return

    url = settings.SELF_PING_URL or f"{settings.BASE_URL.rstrip('/')}/health"
    timeout = httpx.Timeout(settings.SELF_PING_TIMEOUT_SECONDS)

    async with httpx.AsyncClient(timeout=timeout) as client:
        for attempt in range(1, settings.SELF_PING_ATTEMPTS + 1):
            try:
                response = await client.get(url)
                response.raise_for_status()
                return
            except (httpx.RequestError, httpx.HTTPStatusError) as exc:
                logger.error(
                    "Self-ping failed (attempt %s/%s) url=%s err=%s",
                    attempt,
                    settings.SELF_PING_ATTEMPTS,
                    url,
                    exc,
                )
                await asyncio.sleep(settings.SELF_PING_SLEEP_SECONDS)
