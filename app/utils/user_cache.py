"""Redis cache for lightweight user chat details.

Strategy: SHORT TTL + ACTIVE ONLY
- Only cache users who are actively being chatted with (60s TTL)
- Bounded memory: max ~200 cached users per process
- Safe invalidation: never crashes if user_id missing
- Self-healing: short TTL means stale data corrects itself fast
"""

from __future__ import annotations

import json
import logging
from collections import OrderedDict

from app.db.redis import get_redis_client
from app.utils.exception import InternalServerErrorException

logger = logging.getLogger(__name__)

CACHE_PREFIX = "chat:user:"
CACHE_TTL = 60  # 60 seconds — short enough to self-heal, long enough to matter
MAX_LOCAL_CACHE = 200  # bounded LRU per process

# Local in-memory LRU to avoid repeated Redis round-trips for the same user
_local_cache: OrderedDict[str, dict] = OrderedDict()


async def get_cached_user(user_id: str) -> dict | None:
    """Return cached user chat data or None. Checks local LRU first, then Redis."""
    # 1. Local LRU (instant, no network)
    if user_id in _local_cache:
        _local_cache.move_to_end(user_id)
        return _local_cache[user_id]

    # 2. Redis
    try:
        redis = await get_redis_client()
        raw = await redis.get(f"{CACHE_PREFIX}{user_id}")
        if raw:
            data = json.loads(raw)
            _local_cache[user_id] = data
            _evict_local_if_needed()
            return data
    except Exception as e:
        raise InternalServerErrorException("Failed to retrieve cached user data") from e
    return None


async def set_cached_user(user_id: str, data: dict) -> None:
    """Store user chat data in both local LRU and Redis."""
    # Local LRU
    _local_cache[user_id] = data
    _evict_local_if_needed()

    # Redis (fire-and-forget)
    try:
        redis = await get_redis_client()
        await redis.set(f"{CACHE_PREFIX}{user_id}", json.dumps(data), ex=CACHE_TTL)
    except Exception as e:
        raise InternalServerErrorException("Failed to store cached user data") from e


async def invalidate_cached_user(user_id: str) -> None:
    """Remove user from cache. Safe to call with any id — never crashes."""
    _local_cache.pop(user_id, None)
    try:
        redis = await get_redis_client()
        await redis.delete(f"{CACHE_PREFIX}{user_id}")
    except Exception as e:
        raise InternalServerErrorException(
            "Failed to invalidate cached user data"
        ) from e


async def invalidate_cached_users(user_ids: list[str]) -> None:
    """Remove multiple users from cache. Safe to call with empty list."""
    if not user_ids:
        return
    for uid in user_ids:
        _local_cache.pop(uid, None)
    try:
        redis = await get_redis_client()
        keys = [f"{CACHE_PREFIX}{uid}" for uid in user_ids if uid]
        if keys:
            await redis.delete(*keys)
    except Exception as e:
        raise InternalServerErrorException(
            "Failed to invalidate cached user data"
        ) from e


def _evict_local_if_needed() -> None:
    """Keep local cache bounded."""
    while len(_local_cache) > MAX_LOCAL_CACHE:
        _local_cache.popitem(last=False)
