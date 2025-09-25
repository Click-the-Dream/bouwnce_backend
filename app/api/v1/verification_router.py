from fastapi import APIRouter

from app.api.dependencies import CurrentVendor, dbSessionDep
from app.schemas.verification import (
    VerificationCreate,
    VerificationResponse,
    VerificationUpdate,
)
from app.service.verification_service import verification_service

router = APIRouter(prefix="/users/verification", tags=["User"])


@router.post(
    "/",
    response_model=VerificationResponse,
    summary="Create Verification details for vendor",
)
async def create_verification(
    vendor: CurrentVendor, db: dbSessionDep, verification_data: VerificationCreate
):
    verification_data.type = verification_data.type.lower()
    verification_data_dict = verification_data.model_dump()

    print(vendor)
    verification_data_dict["user_id"] = vendor.id

    return await verification_service.create(verification_data_dict, db)


@router.put(
    "/",
    response_model=VerificationResponse,
    summary="Update Verification details for vendor",
)
async def update_verification(
    vendor: CurrentVendor, db: dbSessionDep, verification_data: VerificationUpdate
):
    verification_data_dict = verification_data.model_dump(exclude_unset=True)

    type = verification_data_dict.get("type", None)
    if type:
        verification_data_dict["type"] = verification_data_dict["type"].lower()

    return await verification_service.update(vendor.id, verification_data_dict, db)


@router.get(
    "/", response_model=VerificationResponse, summary="Get Vendor Verification details"
)
async def get_verification(vendor: CurrentVendor, db: dbSessionDep):
    return await verification_service.get(vendor.id, db)
