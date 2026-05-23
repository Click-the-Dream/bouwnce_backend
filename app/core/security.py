import hashlib
import hmac
import secrets
import uuid
from datetime import UTC, datetime, timedelta
from typing import Any

import jwt
from fastapi import HTTPException
from passlib.context import CryptContext

from app.core.config import settings
from app.utils.helper import parse_duration

crytp = CryptContext(schemes=["bcrypt"], deprecated=["auto"])


def create_token(
    subject: str | Any, expires_delta: timedelta | None = None, type: str = "access"
) -> str:

    now = datetime.now(UTC)
    to_encode = {
        "sub": str(subject),
        "iat": now,
        "jti": str(uuid.uuid4()),
        "type": type,
    }
    if expires_delta:
        expiry_time = datetime.now(UTC) + expires_delta
        to_encode["exp"] = expiry_time

    encoded_jwt = jwt.encode(
        to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM
    )

    return encoded_jwt


def create_access_token(subject: str | Any) -> str:
    expires_delta = parse_duration(settings.ACCESS_TOKEN_TTL)

    return create_token(subject=subject, expires_delta=expires_delta, type="access")


def create_refresh_token(subject: str | Any) -> str:
    expires_delta = parse_duration(settings.REFRESH_TOKEN_TTL)

    return create_token(subject=subject, expires_delta=expires_delta, type="refresh")


def verify_token(token: str) -> dict[str, Any]:

    try:
        subject = jwt.decode(token, settings.SECRET_KEY, algorithms=settings.ALGORITHM)
        return subject
    except Exception:
        raise HTTPException(
            status_code=401,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        ) from None


def hash_token(token: str) -> str:
    return hmac.new(
        settings.SECRET_KEY.encode(), token.encode(), hashlib.sha256
    ).hexdigest()


def verify_hashed_token(new_token: str, hashed_token: str) -> bool:
    new_hashed_token = hash_token(new_token)
    return new_hashed_token == hashed_token


def hash_password(data: str) -> str:
    return crytp.hash(data)


def verify_password(plain_data: str, hashed_data: str) -> bool:
    return crytp.verify(plain_data, hashed_data)


def set_cookies(response, key: str, value: str, max_age: int) -> None:
    if settings.NAME == "production":
        response.set_cookie(
            key=key,
            value=value,
            httponly=True,
            max_age=max_age,
            secure=True,
            samesite="lax",
            path="/",
        )

    else:
        response.set_cookie(
            key=key,
            value=value,
            httponly=True,
            max_age=max_age,
            path="/",
            samesite="none",
            secure=True,
        )


def genrate_verification_code() -> str:
    return str(secrets.randbelow(900000) + 100000)
