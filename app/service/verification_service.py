from typing import Any

from fastapi import status
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User
from app.models.verification import Verification
from app.utils.exception import InternalServerErrorException, NotFoundException
from app.utils.responses import response_builder


class VerificationService:
    async def create(
        self, verification_data: dict[str, Any], db: AsyncSession
    ) -> dict[str, Any]:
        try:
            new_verf = await Verification.create(verification_data, db)

            return response_builder(
                status_code=status.HTTP_201_CREATED,
                status="success",
                message="NIN verification has commenced",
                data=new_verf.to_dict(),
            )
        except Exception:
            raise InternalServerErrorException(
                message="Error creating NIN verification"
            ) from None

    async def update(
        self, user_id: str, data: dict[str, Any], db: AsyncSession
    ) -> dict[str, Any]:
        try:
            verification_data = await Verification.get_by(
                filter={"user_id": user_id}, db=db
            )

            if len(verification_data["data"]) == 0:
                raise NotFoundException(
                    message="User does not have any verification details"
                )

            verification = verification_data["data"][0]

            update_verification = await Verification.update_by_id(
                verification.id, data, db
            )

            return response_builder(
                status_code=status.HTTP_200_OK,
                status="success",
                message="verification data is updated successfuly",
                data=update_verification.to_dict(),
            )
        except Exception as e:
            print("Error occured when updating verification details: ", str(e))
            raise InternalServerErrorException(
                message="Error updating user verification data"
            ) from None

    async def get(self, user_id: User, db: AsyncSession) -> dict[str, Any]:
        try:
            verification_data = await Verification.get_by(
                filter={"user_id": user_id}, db=db
            )

            if len(verification_data["data"]) == 0:
                raise NotFoundException(
                    message="There is no verification details for this user"
                )

            verification = verification_data["data"][0]

            return response_builder(
                status_code=status.HTTP_200_OK,
                status="success",
                message="successfully retrieved user verification details",
                data=verification.to_dict(),
            )

        except Exception as e:
            print("Error occured when getting user verification: ", str(e))
            raise InternalServerErrorException(
                message="Error occured when getting user verification details"
            ) from None


verification_service = VerificationService()
