from typing import Any

from fastapi import status
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User
from app.models.verification import Verification
from app.schemas.verification import VerificationResponse
from app.utils.responses import response_builder


class VerificationService:
    async def create(self, verification_data: dict[str, Any], db: AsyncSession):
        try:
            new_verf = await Verification.create(verification_data, db)

            verification_response = VerificationResponse(**new_verf.to_dict())

            return response_builder(
                status_code=status.HTTP_201_CREATED,
                status="success",
                message="NIN verification has commenced",
                data=verification_response,
            )
        except Exception:
            return response_builder(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                status="error",
                message="Error creating NIN verification",
            )

    async def update(self, user_id: str, data: dict[str, Any], db: AsyncSession):
        try:
            verification_data = await Verification.get_by(
                filter={"user_id": user_id}, db=db
            )

            if len(verification_data["data"]) == 0:
                return response_builder(
                    status_code=status.HTTP_404_NOT_FOUND,
                    staus="error",
                    message="User does not have any verification details",
                )
            verification = verification_data["data"][0]

            update_verification = await Verification.update_by_id(
                verification.id, data, db
            )

            verification_response = VerificationResponse(
                **update_verification.to_dict()
            )

            return response_builder(
                status_code=status.HTTP_200_OK,
                status="success",
                message="verification data is updated successfuly",
                data=verification_response,
            )
        except Exception as e:
            print("Error occured when updating verification details: ", str(e))
            return response_builder(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                status="error",
                message="Error updating user verification data",
            )

    async def get(self, user_id: User, db: AsyncSession):
        try:
            verification_data = await Verification.get_by(
                filter={"user_id": user_id}, db=db
            )

            if len(verification_data["data"]) == 0:
                return response_builder(
                    status_code=status.HTTP_404_NOT_FOUND,
                    status="error",
                    message="There is no verification details for this user",
                )
            verification = verification_data["data"][0]

            verification_response = VerificationResponse(**verification.to_dict())

            return response_builder(
                status_code=status.HTTP_200_OK,
                status="success",
                message="successfully retrieved user verification details",
                data=verification_response,
            )

        except Exception as e:
            print("Error occured when getting user verification: ", str(e))
            return response_builder(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                status="error",
                message="Error occured when getting user verification details",
            )


verification_service = VerificationService()
