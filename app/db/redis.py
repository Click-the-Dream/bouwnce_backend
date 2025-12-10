import redis.asyncio as redis

from app.core.config import settings


async def get_redis_client() -> redis.Redis:
    try:
        redis_client = redis.from_url(settings.REDIS_URL, decode_responses=True)
        await redis_client.ping()

        print("✅ Redis connected successfully")
        return redis_client
    except redis.ConnectionError as e:
        print("❌ Failed to connect to Redis")
        print(f"Error: {e}")
