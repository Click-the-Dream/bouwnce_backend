from datetime import UTC, datetime, timedelta
from typing import Any

from fastapi import status
from fastapi.security import HTTPAuthorizationCredentials
from redis import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import create_access_token
from app.models.user import User
from app.schemas.user import UserResponse
from app.utils.emails import generate_login_verification_email, send_email
from app.utils.responses import response_builder


class AuthService:
    async def create_user(
        self, user_data: dict[str, Any], db: AsyncSession, background_tasks
    ):
        user = await User.get_by_unique(
            db=db, email=user_data["email"], username=user_data["username"]
        )
        if user or user.is_deleted:
            if user.email == user_data["email"]:
                return response_builder(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    status="error",
                    message="User with the email already exist",
                )
            else:
                return response_builder(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    status="error",
                    message="User with the username already exist",
                )

        try:
            new_user = await User.create(user_data, db)

            otp = await new_user.generate_otp(db)

            email_data = generate_login_verification_email(new_user.username, otp)
            background_tasks.add_task(
                send_email,
                email_to=new_user.email,
                subject=email_data.subject,
                html_content=email_data.html_content,
            )

            user_data = UserResponse(**new_user.to_dict())

            return response_builder(
                status_code=status.HTTP_201_CREATED,
                status="success",
                message="Successfully created the user, a verification code is sent to the specified email",
                data=user_data,
            )
        except Exception as e:
            print("Error occured creating user: ", str(e))
            return response_builder(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                status="error",
                message="Error occured when creating user",
            )

    async def verify_code(self, user_data: dict[str, Any], db: AsyncSession):

        try:
            user = await User.get_by_unique(db=db, email=user_data["email"])

            if user is None:
                return response_builder(
                    status_code=status.HTTP_404_NOT_FOUND,
                    status="error",
                    message="User with the email does not exist",
                )

            if user.otp != user_data["code"] or user.otp_time < datetime.now(UTC):
                return response_builder(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    status="error",
                    message="Invalid or expired verification code",
                )

            await user.clear_otp(db)

            user_data = UserResponse(**user.to_dict())
            access_token = create_access_token(subject=user.id)
            return response_builder(
                status_code=status.HTTP_200_OK,
                status="success",
                message="Successfully logged in",
                data={"user": user_data, "access_token": access_token},
            )
        except Exception as e:
            print("Error occured verifying code: ", str(e))
            return response_builder(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                status="error",
                message="Error occured when verifying code",
            )

    async def login_user(self, user_email: str, db: AsyncSession, background_tasks):
        try:
            user = await User.get_by_unique(db=db, email=user_email)

            if user is None:
                return response_builder(
                    status_code=status.HTTP_404_NOT_FOUND,
                    status="error",
                    message="User with the email does not exist",
                )

            otp = await user.generate_otp(db)

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
            )
        except Exception as e:
            print("❌Error occured logging in user: ", str(e))
            return response_builder(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                status="error",
                message="Error occured when logging in user",
            )

    async def logout_user(self, auth: HTTPAuthorizationCredentials, redis_db: Redis):
        try:
            authorization_token = auth.credentials

            if not authorization_token:
                return response_builder(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    status="error",
                    message="Authorization token is missing",
                )
            redis_db.setex(
                f"blacklist_{authorization_token}", timedelta(days=30), "blacklisted"
            )

            return response_builder(
                status_code=status.HTTP_200_OK,
                status="success",
                message="Successfully logged out",
            )
        except Exception as e:
            print("❌Error occured logging out user: ", str(e))
            return response_builder(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                status="error",
                message="Error occured when logging out user",
            )


auth_service = AuthService()
