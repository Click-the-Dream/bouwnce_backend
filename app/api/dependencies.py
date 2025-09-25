from collections.abc import AsyncGenerator
from typing import Annotated

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from redis import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import verify_token

# from app.db.mongo import mongo_session
from app.db.postgres_db_conn import get_async_session
from app.db.redis import redis_client
from app.models.user import User

oauth2_scheme = HTTPBearer()


TokenDep = Annotated[HTTPAuthorizationCredentials, Depends(oauth2_scheme)]


async def get_postgres_db() -> AsyncGenerator[AsyncSession, None]:

    async with get_async_session() as session:
        yield session


# async def get_mongo_db():
#     async with mongo_session() as (database, session):
#         yield database, session


def get_redis():
    try:
        yield redis_client
    finally:
        pass


dbSessionDep = Annotated[AsyncSession, Depends(get_postgres_db)]
redisSessionDep = Annotated[Redis, Depends(get_redis)]


async def get_current_user(
    auth: TokenDep,
    db: dbSessionDep,
    redis_db: redisSessionDep,
) -> User | None:

    token = auth.credentials

    is_blacklisted = redis_db.get(f"blacklist_{token}")

    if is_blacklisted:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has been revoked",
            headers={"WWW-Authenticate": "Bearer"},
        )
    try:
        payload = verify_token(token)
        user_id: str = payload.get("sub")
        if user_id is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Could not validate credentials",
                headers={"WWW-Authenticate": "Bearer"},
            )
        user = await User.get_by_id(user_id, db)
        if user is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Could not validate credentials",
                headers={"WWW-Authenticate": "Bearer"},
            )
        return user

    except Exception:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        ) from None


CurrentUser = Annotated[User, Depends(get_current_user)]


async def get_current_vendor(
    current_user: CurrentUser,
) -> User | None:
    print(current_user.role)
    if current_user.role != "vendor":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="The user doesn't have enough privileges",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return current_user


CurrentVendor = Annotated[User, Depends(get_current_vendor)]


async def get_current_admin(
    current_user: CurrentUser,
) -> User | None:
    if current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="The user doesn't have enough privileges",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return current_user


CurrentAdmin = Annotated[User, Depends(get_current_admin)]
