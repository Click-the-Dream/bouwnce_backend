import asyncio

import httpx

from app.core.config import settings


async def call_health_endpoint_cron_task():
    print("cron job is startting")
    async with httpx.AsyncClient() as client:
        for _ in range(10):
            await client.get(f"{settings.BASE_URL}/health")
            await asyncio.sleep(1)
