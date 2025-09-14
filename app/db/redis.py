import redis

from app.core.config import settings

try:
    redis_client = redis.Redis.from_url(settings.REDIS_URL, decode_responses=True)
    redis_client.ping()

    print("✅ Redis connected successfully")
except redis.ConnectionError as e:
    print("❌ Failed to connect to Redis")
    print(f"Error: {e}")
