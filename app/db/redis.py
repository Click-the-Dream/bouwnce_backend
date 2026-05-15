from __future__ import annotations

import asyncio

import redis.asyncio as redis

from app.core.config import settings

_client_lock = asyncio.Lock()
_redis_client: redis.Redis | None = None


async def get_redis_client() -> redis.Redis:
    """
    Return a singleton Redis client backed by a shared connection pool.

    Why: endpoints like long-poll `XREAD BLOCK` can hold connections for a long time.
    Creating a new client per request can exhaust Redis connections and degrade websocket
    performance.
    """
    global _redis_client
    if _redis_client is not None:
        return _redis_client

    async with _client_lock:
        if _redis_client is not None:
            return _redis_client

        pool = redis.ConnectionPool.from_url(
            settings.REDIS_URL,
            decode_responses=True,
            max_connections=int(getattr(settings, "REDIS_MAX_CONNECTIONS", 200)),
            health_check_interval=int(getattr(settings, "REDIS_HEALTH_CHECK_INTERVAL", 30)),
        )
        _redis_client = redis.Redis(connection_pool=pool)
        # Verify connection once at startup/first use
        await _redis_client.ping()
        return _redis_client


async def close_redis_client() -> None:
    global _redis_client
    if _redis_client is None:
        return
    try:
        await _redis_client.aclose()
    finally:
        _redis_client = None
