import secrets
import uuid
from datetime import UTC, datetime, timedelta
from typing import Any

import jwt
from fastapi import HTTPException
from passlib.context import CryptContext

from app.core.config import settings

pwd = CryptContext(schemes=["bcrypt"], deprecated=["auto"])


def create_access_token(
    subject: str | Any, expires_delta: timedelta | None = None
) -> str:

    now = datetime.now(UTC)
    to_encode = {"sub": str(subject), "iat": now, "jti": str(uuid.uuid4())}
    if expires_delta:
        expiry_time = datetime.now(UTC) + expires_delta
        to_encode["exp"] = expiry_time

    encoded_jwt = jwt.encode(
        to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM
    )

    return encoded_jwt


def verify_token(token: str) -> str:

    try:
        subject = jwt.decode(token, settings.SECRET_KEY, algorithms=settings.ALGORITHM)
        return subject
    except Exception:
        raise HTTPException(
            status_code=401,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        ) from None


def hash_password(password: str) -> str:
    return pwd.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd.verify(plain_password, hashed_password)


def genrate_verification_code() -> str:
    return str(secrets.randbelow(900000) + 100000)
