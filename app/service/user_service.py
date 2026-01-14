# me, get user by ID, update user, delete user, list users (with search and pagination)
from typing import Any

from fastapi import status
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User
from app.utils.exception import (
    BadRequestException,
    NotFoundException,
)
from app.utils.responses import response_builder


class UserService:

    async def get_me(self, user: User) -> dict[str, Any]:

        return response_builder(
            status_code=status.HTTP_200_OK,
            status="success",
            message="Successfully fetched user data",
            data=user.to_dict(),
        )

    async def get_user_by_id(self, user_id: str, db: AsyncSession) -> dict[str, Any]:

        try:
            user = await User.get_by_id(user_id, db)

            if not user:
                raise NotFoundException(message="User not found")

            return response_builder(
                status_code=status.HTTP_200_OK,
                status="success",
                message="Successfully fetched user data",
                data=user.to_dict(),
            )
        except ValueError as ve:
            raise NotFoundException(message=str(ve)) from None
        except TypeError as te:
            raise BadRequestException(message=str(te)) from None

    async def update_user(
        self, user_id: str, user_data: dict[str, Any], db: AsyncSession
    ) -> dict[str, Any]:

        try:
            user = await User.update_by_id(user_id, user_data, db)

            return response_builder(
                status_code=status.HTTP_200_OK,
                status="success",
                message="Successfully updated user data",
                data=user.to_dict(),
            )
        except ValueError as ve:
            raise NotFoundException(message=str(ve)) from None

        except TypeError as te:
            raise BadRequestException(message=str(te)) from None

    async def update_me(
        self, user: User, user_data: dict[str, Any], db: AsyncSession
    ) -> dict[str, Any]:

        user = await user.update_me(user_data, db)

        return response_builder(
            status_code=status.HTTP_200_OK,
            status="success",
            message="Successfully updated user data",
            data=user.to_dict(),
        )

    async def deactivate_user(self, user: User, db: AsyncSession) -> dict[str, Any]:

        user.is_active = False
        await user.save()

        return response_builder(
            status_code=status.HTTP_200_OK,
            status="success",
            message="User account has be deactivated successfully",
        )

    async def activate_user(self, user: User, db: AsyncSession) -> dict[str, Any]:

        user.is_active = True
        await user.save()

        return response_builder(
            status_code=status.HTTP_200_OK,
            status="success",
            message="User account has been successfully activated",
        )

    async def delete_user_by_id(self, user_id: str, db: AsyncSession) -> dict[str, Any]:

        try:
            await User.delete_by_id(user_id, db)

            return response_builder(
                status_code=status.HTTP_204_NO_CONTENT,
                status="success",
                message="Successfully deleted user",
            )
        except ValueError as ve:
            raise NotFoundException(message=str(ve)) from None
        except TypeError as te:
            raise BadRequestException(message=str(te)) from None

    async def delete_me(self, user: User, db: AsyncSession) -> dict[str, Any]:

        user = await user.delete_me(db)

        return response_builder(
            status_code=status.HTTP_204_NO_CONTENT,
            status="success",
            message="Successfully deleted user",
        )

    async def undelete_user_by_id(
        self, user_id: str, db: AsyncSession
    ) -> dict[str, Any]:

        try:
            user = await User.undelete_by_id(user_id, db)

            return response_builder(
                status_code=status.HTTP_200_OK,
                status="success",
                message="Successfully undeleted user",
                data=user.to_dict(),
            )
        except ValueError as ve:
            raise NotFoundException(message=str(ve)) from None
        except TypeError as te:
            raise BadRequestException(message=str(te)) from None

    async def list_users(
        self,
        db: AsyncSession,
        search: str | None = None,
        page: int | None = 1,
        page_size: int | None = 10,
    ) -> dict[str, Any]:

        filter = {}
        if search:
            filter = {
                "username": f"%{search}%",
                "email": f"%{search}%",
                "full_name": f"%{search}%",
            }
        users = await User.get_by(filter=filter, db=db, page=page, page_size=page_size)

        users_data = [user.to_dict() for user in users["data"]]

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


user_service = UserService()
