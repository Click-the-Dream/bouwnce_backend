import uuid
from datetime import UTC, datetime
from typing import Any

from fastapi import Request, Response, status
from fastapi.security import HTTPAuthorizationCredentials
from redis import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.security import (
    create_access_token,
    create_refresh_token,
    hash_token,
    set_cookies,
    verify_hashed_token,
    verify_token,
)
from app.models.refresh_token import RefreshToken
from app.models.user import User
from app.models.wallet import UserWallet
from app.utils.emails import generate_login_verification_email, send_email
from app.utils.exception import (
    BadRequestException,
    InternalServerErrorException,
    NotFoundException,
    UnAuthorizedException,
)
from app.utils.helper import parse_duration
from app.utils.responses import response_builder


class AuthService:
    async def create_user(
        self, user_data: dict[str, Any], db: AsyncSession, background_tasks
    ):
        user = await User.get_by_unique(
            db=db, email=user_data["email"], username=user_data["username"]
        )

        if user:
            if user.email == user_data["email"]:
                raise BadRequestException(message="User with the email already exist")
            else:
                raise BadRequestException(
                    message="User with the username already exist"
                )
        user_data["is_store_owner"] = False
        try:
            new_user = await User.create(user_data, db)

            await UserWallet.create({"user_id": new_user.id}, db=db)
            otp = await new_user.generate_otp(db)
            # Ensure OTP is persisted before returning it to the client (avoids race with /verify-code)
            await db.commit()

        except Exception:
            raise InternalServerErrorException(
                message="Error occured when creating user"
            ) from e

        email_data = generate_login_verification_email(new_user.username, otp)
        background_tasks.add_task(
            send_email,
            email_to=new_user.email,
            subject=email_data.subject,
            html_content=email_data.html_content,
        )

        user_data = new_user.to_dict()

        # Temporarily for before email service works perfectly
        user_data["otp"] = otp

        return response_builder(
            status_code=status.HTTP_201_CREATED,
            status="success",
            message="Successfully created the user, a verification code is sent to the specified email",
            data=user_data,
        )

    async def verify_code(
        self,
        user_data: dict[str, Any],
        db: AsyncSession,
        request: Request,
        response: Response,
    ):

        # Get request  metadata
        device_id = request.cookies.get("device_id", None)
        ip_address = request.client.host if request.client else "unknown"
        user_agent = request.headers.get("user-agent", "unknown")

        user = await User.get_by_unique(db=db, email=user_data["email"])
        if user is None:
            raise NotFoundException(message="User with the email does not exist")

        code = (user_data.get("code") or "").strip()
        now = datetime.now(UTC)
        if (
            not user.otp
            or not user.otp_time
            or user.otp != code
            or user.otp_time <= now
        ):
            raise BadRequestException(message="Invalid or expired verification code")

        await user.clear_otp(db)

        # user_data = UserResponse(**user.to_dict())
        access_token = create_access_token(subject=user.id)

        # Generate device_id cookie if not exists
        new_device_id = device_id if device_id else str(uuid.uuid4())

        # generate refresh token
        refresh_token_expires_at = datetime.now(UTC) + parse_duration(
            settings.REFRESH_TOKEN_TTL
        )

        refresh_token = create_refresh_token(subject=user.id)
        hashed_refresh_token = hash_token(refresh_token)
        await RefreshToken.create_refresh_token(
            user_id=str(user.id),
            token=hashed_refresh_token,
            device_id=new_device_id,
            user_agent=user_agent,
            ip_address=ip_address,
            expires_at=refresh_token_expires_at,
            db=db,
        )
        max_age = int(parse_duration(settings.REFRESH_TOKEN_TTL).total_seconds())

        if not device_id:
            set_cookies(
                response, "device_id", new_device_id, max_age=31536000
            )  # Setting the device_id cookie to 1 year

        set_cookies(response, "refresh_token", refresh_token, max_age)

        return response_builder(
            status_code=status.HTTP_200_OK,
            status="success",
            message="Successfully logged in",
            data={"user": user.to_dict(), "access_token": access_token},
        )

    async def login_user(self, user_email: str, db: AsyncSession, background_tasks):

        user = await User.get_by_unique(db=db, email=user_email)

        if user is None:
            raise NotFoundException(message="User with the email does not exist")
        otp = await user.generate_otp(db)
        # Ensure OTP is persisted before returning it to the client (avoids race with /verify-code)
        await db.commit()

        email_data = generate_login_verification_email(user.username, otp)
        background_tasks.add_task(
            send_email,
            email_to=user.email,
            subject=email_data.subject,
            html_content=email_data.html_content,
        )

        return response_builder(
            status_code=status.HTTP_200_OK,
            status="success",
            message="A verification code is sent to the specified email",
            data={"otp": otp},  # Temporarily for before email service works perfectly
        )

    async def logout_user(
        self,
        user_id: str,
        auth: HTTPAuthorizationCredentials,
        redis_db: Redis,
        db: AsyncSession,
        request: Request,
        response: Response,
    ):

        authorization_token = auth.credentials

        if not authorization_token:
            raise BadRequestException(message="Authorization token is missing")

        # Blacklist access token for the remaining time to expire
        payload = verify_token(authorization_token)
        expiry_time = payload.get("exp")

        if not expiry_time:
            expiry_datetime = parse_duration(settings.ACCESS_TOKEN_TTL)
            await redis_db.setex(
                f"blacklist_{authorization_token}", expiry_datetime, "blacklisted"
            )
        else:
            expiry_datetime = datetime.fromtimestamp(expiry_time, tz=UTC)
            remaining_time = expiry_datetime - datetime.now(UTC)
            await redis_db.setex(
                f"blacklist_{authorization_token}", remaining_time, "blacklisted"
            )

        # Get refresh token from cookies and revoke it
        device_id = request.cookies.get("device_id", None)
        if device_id:
            refresh_token = await RefreshToken.get_token_by_user_and_device(
                user_id, device_id, db
            )
            if refresh_token:
                await refresh_token.revoke(db)

        # clear cookies
        response.delete_cookie("refresh_token", path="/")

        return response_builder(
            status_code=status.HTTP_200_OK,
            status="success",
            message="Successfully logged out",
        )

    async def refresh_access_token(
        self, request: Request, response: Response, db: AsyncSession
    ):
        # Get device_id from cookies
        device_id = request.cookies.get("device_id", None)
        if not device_id:
            raise BadRequestException(message="Device ID is missing in cookies")

        # Get refresh_token from cookies
        refresh_token = request.cookies.get("refresh_token", None)
        if not refresh_token:
            raise BadRequestException(message="Refresh token is missing in cookies")

        try:
            payload = verify_token(refresh_token)
        except Exception:
            raise UnAuthorizedException(message="Invalid refresh token") from None

        user_id: str = payload.get("sub")
        if not user_id:
            raise UnAuthorizedException(message="could not validate credentials")

        type = payload.get("type")
        if type != "refresh":
            raise UnAuthorizedException(message="Invalid token type")

        user = await User.get_by_id(user_id, db)
        if not user:
            raise UnAuthorizedException(message="Could not validate credentials")
        store_refresh_token = await RefreshToken.get_token_by_user_and_device(
            user_id, device_id, db
        )
        if not store_refresh_token:
            raise UnAuthorizedException(
                message="Refresh token revoked or not found. Please login again"
            )

        if not verify_hashed_token(refresh_token, store_refresh_token.token):
            raise UnAuthorizedException(
                message="Invalid refresh token. Please login again"
            )

        # Create new access token
        access_token = create_access_token(subject=user.id)

        # Create a new refresh token
        refresh_token_expires_at = datetime.now(UTC) + parse_duration(
            settings.REFRESH_TOKEN_TTL
        )
        new_refresh_token = create_refresh_token(subject=user.id)
        hashed_refresh_token = hash_token(new_refresh_token)

        await RefreshToken.create_refresh_token(
            user_id=str(user.id),
            token=hashed_refresh_token,
            device_id=device_id,
            user_agent=request.headers.get("user-agent", "unknown"),
            ip_address=request.client.host if request.client else "unknown",
            expires_at=refresh_token_expires_at,
            db=db,
        )

        # Set new refresh token in cookies
        max_age = int(parse_duration(settings.REFRESH_TOKEN_TTL).total_seconds())
        set_cookies(response, "refresh_token", new_refresh_token, max_age)

        return response_builder(
            status_code=status.HTTP_200_OK,
            status="success",
            message="Access token refreshed successfully",
            data={"access_token": access_token},
        )


auth_service = AuthService()
