# me, get user by ID, update user, delete user, list users (with search and pagination)
from typing import Any

from fastapi import status
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User
from app.utils.exception import (
    BadRequestException,
    InternalServerErrorException,
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
        except Exception as e:
            print("Error occured fetching user by ID: ", str(e))
            raise InternalServerErrorException(
                message="Error occured when fetching user by ID"
            ) from None

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
        except Exception as e:
            print("Error occured updating user: ", str(e))
            raise InternalServerErrorException(
                message="Error occured when updating user data"
            ) from None

    async def update_me(
        self, user: User, user_data: dict[str, Any], db: AsyncSession
    ) -> dict[str, Any]:
        try:
            user = await user.update_me(user_data, db)

            return response_builder(
                status_code=status.HTTP_200_OK,
                status="success",
                message="Successfully updated user data",
                data=user.to_dict(),
            )
        except Exception as e:
            print("Error occured updating user: ", str(e))
            raise InternalServerErrorException(
                message="Error occured when updating user data"
            ) from None

    async def deactivate_user(self, user: User, db: AsyncSession) -> dict[str, Any]:
        try:
            user.is_active = False
            await user.save()

            return response_builder(
                status_code=status.HTTP_200_OK,
                status="success",
                message="User account has be deactivated successfully",
            )
        except Exception as e:
            print("Error occured while deactivating user: ", str(e))
            raise InternalServerErrorException(
                message="Error occured while deactivating user account"
            ) from None

    async def activate_user(self, user: User, db: AsyncSession) -> dict[str, Any]:
        try:
            user.is_active = True
            await user.save()

            return response_builder(
                status_code=status.HTTP_200_OK,
                status="success",
                message="User account has been successfully activated",
            )
        except Exception as e:
            print("Error occured while activating user account: ", str(e))
            raise InternalServerErrorException(
                message="Error occured while activating user account"
            ) from None

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
        except Exception as e:
            print("Error occured deleting user: ", str(e))
            raise InternalServerErrorException(
                message="Error occured  when deleting user"
            ) from None

    async def delete_me(self, user: User, db: AsyncSession) -> dict[str, Any]:

        try:
            user = await user.delete_me(db)

            return response_builder(
                status_code=status.HTTP_204_NO_CONTENT,
                status="success",
                message="Successfully deleted user",
            )
        except Exception as e:
            print("Error occured deleting user: ", str(e))
            raise InternalServerErrorException(
                message="Error occured when deleting user"
            ) from None

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
        except Exception as e:
            print("Error occured undeleting user: ", str(e))
            raise InternalServerErrorException(
                message="Error occured when undeleting user"
            ) from None

    async def list_users(
        self,
        db: AsyncSession,
        search: str | None = None,
        page: int | None = 1,
        page_size: int | None = 10,
    ) -> dict[str, Any]:

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
        except Exception as e:
            print("Error occured fetching users: ", str(e))
            raise InternalServerErrorException(
                message="Error occured while fetching users"
            ) from None


user_service = UserService()
