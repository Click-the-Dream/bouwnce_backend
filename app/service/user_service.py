# me, get user by ID, update user, delete user, list users (with search and pagination)
from typing import Any

from fastapi import status
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User
from app.schemas.user import UserResponse
from app.utils.responses import response_builder


class UserService:

    async def get_me(self, user: User) -> UserResponse:
        data = UserResponse(**user.to_dict())
        return response_builder(
            status_code=status.HTTP_200_OK,
            status="success",
            message="Successfully fetched user data",
            data=data,
        )

    async def get_user_by_id(self, user_id: str, db: AsyncSession) -> UserResponse:

        try:
            user = await User.get_by_id(user_id, db)

            if not user:
                return response_builder(
                    status_code=status.HTTP_404_NOT_FOUND,
                    status="error",
                    message="User not found",
                )

            data = UserResponse(**user.to_dict())
            return response_builder(
                status_code=status.HTTP_200_OK,
                status="success",
                message="Successfully fetched user data",
                data=data,
            )
        except Exception as e:
            print("Error occured fetching user by ID: ", str(e))
            return response_builder(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                status="error",
                message="Error occured when fetching user by ID",
            )

    async def update_user(
        self, user_id: str, user_data: dict[str, Any], db: AsyncSession
    ) -> UserResponse:

        try:
            user = await User.update_by_id(user_id, user_data, db)

            user_data = UserResponse(**user.to_dict())

            return response_builder(
                status_code=status.HTTP_200_OK,
                status="success",
                message="Successfully updated user data",
                data=user_data,
            )
        except ValueError as ve:
            return response_builder(
                status_code=status.HTTP_404_NOT_FOUND, status="error", message=str(ve)
            )
        except Exception as e:
            print("Error occured updating user: ", str(e))
            return response_builder(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                status="error",
                message="Error occured when updating user data",
            )

    async def update_me(
        self, user: User, user_data: dict[str, Any], db: AsyncSession
    ) -> UserResponse:
        try:
            user = await user.update_me(user_data, db)

            user_data = UserResponse(**user.to_dict())

            return response_builder(
                status_code=status.HTTP_200_OK,
                status="success",
                message="Successfully updated user data",
                data=user_data,
            )
        except Exception as e:
            print("Error occured updating user: ", str(e))
            return response_builder(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                status="error",
                message="Error occured when updating user data",
            )

    async def delete_user_by_id(self, user_id: str, db: AsyncSession) -> UserResponse:

        try:
            user = await User.delete_by_id(user_id, db)

            user_data = UserResponse(**user.to_dict())

            return response_builder(
                status_code=status.HTTP_200_OK,
                status="success",
                message="Successfully deleted user",
                data=user_data,
            )
        except ValueError as ve:
            return response_builder(
                status_code=status.HTTP_404_NOT_FOUND, status="error", message=str(ve)
            )
        except Exception as e:
            print("Error occured deleting user: ", str(e))
            return response_builder(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                status="error",
                message="Error occured  when deleting user",
            )

    async def delete_me(self, user: User, db: AsyncSession) -> UserResponse:

        try:
            user = await user.delete_me(db)

            user_data = UserResponse(**user.to_dict())

            return response_builder(
                status_code=status.HTTP_200_OK,
                status="success",
                message="Successfully deleted user",
                data=user_data,
            )
        except Exception as e:
            print("Error occured deleting user: ", str(e))
            return response_builder(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                status="error",
                message="Error occured when deleting user",
            )

    async def undelete_user_by_id(self, user_id: str, db: AsyncSession) -> UserResponse:

        try:
            user = await User.undelete_by_id(user_id, db)

            user_data = UserResponse(**user.to_dict())

            return response_builder(
                status_code=status.HTTP_200_OK,
                status="success",
                message="Successfully undeleted user",
                data=user_data,
            )
        except ValueError as ve:
            return response_builder(
                status_code=status.HTTP_404_NOT_FOUND, status="error", message=str(ve)
            )
        except Exception as e:
            print("Error occured undeleting user: ", str(e))
            return response_builder(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                status="error",
                message="Error occured when undeleting user",
            )

    async def list_users(
        self,
        db: AsyncSession,
        search: str | None = None,
        page: int | None = 1,
        page_size: int | None = 10,
    ) -> UserResponse:

        try:
            filter = {}
            if search:
                filter = {
                    "username": f"%{search}%",
                    "email": f"%{search}%",
                    "full_name": f"%{search}%",
                }
            users = await User.get_by(
                filter=filter, db=db, page=page, page_size=page_size
            )

            users_data = [UserResponse(**user.to_dict()) for user in users["data"]]

            return response_builder(
                status_code=status.HTTP_200_OK,
                status="success",
                message="Successfully fetched users",
                data={
                    "users": users_data,
                    "total": users["total"],
                    "page": users["page"],
                    "page_size": users["page_size"],
                },
            )
        except Exception as e:
            print("Error occured fetching users: ", str(e))
            return response_builder(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                status="error",
                message="Error occured when fetching users",
            )


user_service = UserService()
