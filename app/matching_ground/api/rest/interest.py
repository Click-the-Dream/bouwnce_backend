from fastapi import APIRouter, status
from uuid import UUID

from app.matching_ground.schema.interest import UserInterestCreate, UserInterestReponse, InterestReponse, BaseResponse
from app.matching_ground.service.interest_service import interest_service
from app.api.dependencies import dbSessionDep, CurrentUser

router = APIRouter(prefix="/interests", tags=["Interests"])


@router.get("/available", status_code=status.HTTP_200_OK, response_model=InterestReponse)
async def get_available_interests(
    db: dbSessionDep,
    _: CurrentUser
):
    return await interest_service.get_all_interests(db)


@router.post("/user", status_code=status.HTTP_201_CREATED,response_model=BaseResponse)
async def add_user_interests(
    db: dbSessionDep,
    current_user: CurrentUser,
    interest_lists: UserInterestCreate
):
    return await interest_service.add_user_interests(db, str(current_user.id), interest_lists.interests)


@router.get("/user", response_model=UserInterestReponse, status_code=status.HTTP_200_OK)
async def get_user_interests(
    db: dbSessionDep,
    current_user: CurrentUser
): 
    return await interest_service.get_user_interests(db, str(current_user.id))

@router.get("/user/{user_id}", response_model=UserInterestReponse, status_code=status.HTTP_200_OK)
async def get_user_interest_by_id(
    user_id: UUID,
    db: dbSessionDep,
    _: CurrentUser
):
    return await interest_service.get_user_interests(db, str(user_id))


@router.put("/user", response_model=BaseResponse, status_code=status.HTTP_200_OK)
async def update_user_interests(
    db: dbSessionDep,
    current_user: CurrentUser,
    interest_lists: UserInterestCreate
):
    return await interest_service.add_user_interests(db, str(current_user.id), interest_lists.interests)


@router.delete("/user", status_code=status.HTTP_204_NO_CONTENT)
async def remove_user_interests(
    db: dbSessionDep,
    current_user: CurrentUser,
    interest_lists: UserInterestCreate
):
    return await interest_service.remove_user_interest(db, str(current_user.id), interest_lists.interests)