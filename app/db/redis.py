from __future__ import annotations

import asyncio

import redis.asyncio as redis

from app.core.config import settings

_client_lock = asyncio.Lock()
_redis_client: redis.Redis | None = None

_blocking_client_lock = asyncio.Lock()
_blocking_redis_client: redis.Redis | None = None


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
            health_check_interval=int(
                getattr(settings, "REDIS_HEALTH_CHECK_INTERVAL", 30)
            ),
            socket_timeout=None,
            socket_connect_timeout=None,
        )
        _redis_client = redis.Redis(connection_pool=pool)
        # Verify connection once at startup/first use
        await _redis_client.ping()
        return _redis_client


def _redis_connection_limit() -> int:
    """Provider's per-process connection cap (0 = unknown / not enforced)."""
    return int(getattr(settings, "REDIS_CONNECTION_LIMIT", 0) or 0)


async def get_blocking_redis_client() -> redis.Redis:
    """
    Return a singleton Redis client with its own, tightly bounded pool, reserved
    for long-blocking reads (`XREAD ... BLOCK`).

    Why: a single ``XREAD BLOCK`` occupies a pooled connection for the entire
    block window.  When those live on the shared pool, a burst of long-poll
    requests drains it and every other Redis user in the process (WebSocket
    fan-out, presence heartbeats, the rate limiter, background jobs) starts
    failing with "Too many connections" — which surfaces to clients as the
    server crashing.  Isolating them means the long-poll traffic can only ever
    exhaust its own small pool.

    When the provider only allows a single connection, isolation is impossible;
    we share the main client so the app still starts and the concurrency
    semaphore keeps blocking reads from holding that one connection too long.
    """
    if _redis_connection_limit() == 1:
        return await get_redis_client()

    global _blocking_redis_client
    if _blocking_redis_client is not None:
        return _blocking_redis_client

    async with _blocking_client_lock:
        if _blocking_redis_client is not None:
            return _blocking_redis_client

        pool = redis.ConnectionPool.from_url(
            settings.REDIS_URL,
            decode_responses=True,
            max_connections=int(
                getattr(settings, "REDIS_BLOCKING_MAX_CONNECTIONS", 20)
            ),
            health_check_interval=int(
                getattr(settings, "REDIS_HEALTH_CHECK_INTERVAL", 30)
            ),
            # Same reason as the shared pool above; long-block reads also
            # need no requirement that a response lands within 5s.
            socket_timeout=None,
            socket_connect_timeout=None,
        )
        _blocking_redis_client = redis.Redis(connection_pool=pool)
        return _blocking_redis_client


async def close_redis_client() -> None:
    global _redis_client, _blocking_redis_client
    try:
        if _redis_client is not None:
            await _redis_client.aclose()
    finally:
        _redis_client = None

    try:
        if _blocking_redis_client is not None:
            await _blocking_redis_client.aclose()
    finally:
        _blocking_redis_client = None
