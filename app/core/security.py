import secrets
from datetime import UTC, datetime, timedelta
from typing import Any

import jwt
from passlib.context import CryptContext

from app.core.config import settings

pwd = CryptContext(schemes=["bcrypt"], deprecated=["auto"])


def create_access_token(subject: str | Any, expires_delta: timedelta) -> str:
    expiry_time = datetime.now(UTC) + expires_delta

    to_encode = {"exp": expiry_time, "sub": str(subject)}
    encoded_jwt = jwt.encode(
        to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM
    )

    return encoded_jwt


def verify_token(token: str) -> str:

    try:
        subject = jwt.decode(token, settings.SECRET_KEY, algorithms=settings.ALGORITHM)
        return subject
    except Exception as e:
        raise e


def hash_password(password: str) -> str:
    return pwd.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd.verify(plain_password, hashed_password)


def genrate_verification_code() -> str:
    return str(secrets.randbelow(900000) + 100000)
