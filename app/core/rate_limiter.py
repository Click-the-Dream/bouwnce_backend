import json
from collections.abc import Awaitable, Callable
from typing import Annotated

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.core.config import settings
from app.core.security import verify_token
from app.db.redis import redis_client

security = HTTPBearer(auto_error=False)

SecurityDep = Annotated[HTTPAuthorizationCredentials, Depends(security)]


class RateLimiter:
    def __init__(self, redis):
        self.redis = redis

    @staticmethod
    def _get_client_ip(request: Request) -> str:
        """Resolve client IP:
        - if X_FORWARDER_FOR found and trusted, take the first IP in the header
        - Otherwise fallback to request.client.host
        """

        if settings.TRUST_X_FORWARDED_FOR:
            x_forwarded_for = request.headers.get("X-Forwarded-For")
            if x_forwarded_for:
                first_ip = x_forwarded_for.split(",")[0].strip()

                if first_ip:
                    return first_ip

        client = request.client
        return client.host if client else "unknown"

    def _incr_and_get(
        self,
        key: str,
        window_seconds: int,
    ) -> int:
        """Increase and set ttl if new

        Args:
            key (str): The key to increment
            window_seconds (int): number of seconds for the rate limit window

        Returns:
            int: The current count after incrementing
        """

        with self.redis.pipeline() as pipe:
            pipe.incr(key)
            pipe.ttl(key)

            res = pipe.execute()

        current_count = int(res[0])
        ttl = res[1]

        if ttl == -1 or ttl == -2:
            self.redis.expire(key, window_seconds)

        return current_count

    def is_rate_limited(
        self,
        key: str,
        times: int,
        seconds: int,
    ) -> tuple[bool, int]:
        """return (is_limited, current_count)"""

        count = self._incr_and_get(key, seconds)

        return (count > times, count)

    def push_abuse_alert(self, payload: dict):
        """Push abuse alert to redis list for further processing"""
        alert_key = "rate_limit:alerts"

        self.redis.rpush(alert_key, json.dumps(payload))

    def rate_limit_dependency(
        self,
        ip_times: int = 100,
        ip_seconds: int = 60,
        user_times: int = 1000,
        user_seconds: int = 60,
        require_auth_for_user_limit: bool = False,
    ) -> Callable[[Request, HTTPAuthorizationCredentials | None], Awaitable[None]]:
        """Factory that return function that enforces:
            - Ip limit: ip_times per ip_seconds
            - User limit: user_times per user_seconds
            if require_auth_for_user_limit is True and no valid JWT, still enforce ip limit only

        Args:
            ip_times (int): number of requests allowed per ip_seconds per IP
            ip_senconds (int): number of seconds for IP rate limit window
            user_times (int): number of requests allowed per user_seconds per user
            user_seconds (int): number of seconds for user rate limit window
            require_auth_for_user_limit (bool, optional): whether to enforce user limit only when valid JWT is provided. Defaults to False.

        Returns:
            Callable[[Request, Optional[HTTPAuthorizationCredentials]], Awaitable[None]]: A dependency function that can be used in FastAPI routes
        """

        def _dependency(
            request: Request,
            credentials: SecurityDep | None = None,
        ):
            ip = self._get_client_ip(request)
            ip_key = f"rl:ip:{ip}:{ip_seconds}:{request.url.path.replace('/', '_')}"

            ip_limit, ip_count = self.is_rate_limited(ip_key, ip_times, ip_seconds)

            if ip_limit:
                alert = {
                    "type": "ip_rate_limit",
                    "ip": ip,
                    "count": ip_count,
                    "limit": ip_times,
                    "windows_seconds": ip_seconds,
                    "path": str(request.url.path),
                    "method": request.method,
                }

                print("IP Rate limit exceeded: ", alert)
                self.push_abuse_alert(alert)
                raise HTTPException(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    detail="Too many requests from this IP address",
                )

            user_id = None
            if credentials and credentials.credentials:
                try:
                    payload = verify_token(credentials.credentials)
                    user_id: str = payload.get("sub")
                except Exception:
                    pass

            if user_id:
                user_key = f"rl:user:{user_id}:{user_seconds}:{request.url.path.replace('/', '_')}"

                user_limit, user_count = self.is_rate_limited(
                    user_key, user_times, user_seconds
                )
                if user_limit:
                    alert = {
                        "type": "user_rate_limit",
                        "user_id": user_id,
                        "count": user_count,
                        "limit": user_times,
                        "windows_seconds": user_seconds,
                        "path": str(request.url.path),
                        "method": request.method,
                    }

                    print("User Rate limit exceeded: ", alert)
                    self.push_abuse_alert(alert)
                    raise HTTPException(
                        status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                        detail="Too many requests from this user account",
                    )

            return None

        return _dependency


rate_limiter = RateLimiter(redis_client)
