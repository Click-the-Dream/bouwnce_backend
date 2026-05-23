from fastapi import APIRouter, Query, UploadFile

from app.api.dependencies import (
    CurrentActiveUser,
    CurrentAdmin,
    CurrentUser,
    dbSessionDep,
)
from app.schemas.user import (
    BaseResponse,
    PaginatedUserResponse,
    UpdateUser,
    UserResponse,
)
from app.service.user_service import user_service

router = APIRouter(prefix="", tags=["User"])


@router.get("/me", summary="Get current user", response_model=UserResponse)
async def get_me(current_user: CurrentUser, db: dbSessionDep) -> UserResponse:

    return await user_service.get_me(current_user)


@router.get("/{user_id}", summary="Get user by ID", response_model=UserResponse)
async def get_user_by_id(
    user_id: str, db: dbSessionDep, _: CurrentActiveUser
) -> UserResponse:

    return await user_service.get_user_by_id(user_id, db)


@router.get(
    "/",
    summary="List users with search and pagination",
    response_model=PaginatedUserResponse,
)
async def list_users(
    db: dbSessionDep,
    _: CurrentActiveUser,
    page: int | None = Query(default=1, gt=0, description="The page number to fetch"),
    per_page: int | None = Query(
        default=10, gt=0, description="The number of products in a page"
    ),
    search: str | None = Query(default=None, description="Search query"),
) -> PaginatedUserResponse:

    return await user_service.list_users(db, search, page, per_page)


@router.put("/profile-picture", response_model=UserResponse)
async def upload_user_pic(
    current_user: CurrentActiveUser, db: dbSessionDep, picture: UploadFile
):
    return await user_service.update_user_profile_pic(current_user, db, picture)


@router.put("/me", summary="Update current user", response_model=UserResponse)
async def update_me(
    user_data: UpdateUser, current_user: CurrentActiveUser, db: dbSessionDep
) -> UserResponse:
    user_data = user_data.model_dump(exclude_unset=True)
    if user_data.get("role", None) is not None:
        user_data["role"] = user_data["role"].value
    return await user_service.update_me(current_user, user_data, db)


@router.put(
    "/me/deactivate", summary="Deactivate user account", response_model=BaseResponse
)
async def deactivate_user(current_user: CurrentUser, db: dbSessionDep) -> BaseResponse:
    return await user_service.deactivate_user(current_user, db)


@router.put(
    "/me/activate", summary="Activate User account", response_model=BaseResponse
)
async def activate_user(current_user: CurrentUser, db: dbSessionDep) -> BaseResponse:
    return await user_service.activate_user(current_user, db)


@router.put(
    "/{user_id}", summary="Update user by ID, only admin", response_model=UserResponse
)
async def update_user_by_id(
    user_id: str, user_data: UpdateUser, db: dbSessionDep, _: CurrentAdmin
) -> UserResponse:

    user_data = user_data.model_dump(exclude_unset=True)
    if user_data.get("role", None) is not None:
        user_data["role"] = user_data["role"].value

    return await user_service.update_user(user_id, user_data, db)


@router.delete("/me", summary="Delete current user", response_model=BaseResponse)
async def delete_me(current_user: CurrentUser, db: dbSessionDep) -> BaseResponse:

    return await user_service.delete_me(current_user, db)


@router.delete(
    "/{user_id}", summary="Delete user by ID, only admin", response_model=BaseResponse
)
async def delete_user(_: CurrentAdmin, user_id: str, db: dbSessionDep) -> BaseResponse:

    return await user_service.delete_user_by_id(user_id, db)


@router.post(
    "/undelete/{user_id}",
    summary="Undelete user by ID, only admin",
    response_model=BaseResponse,
)
async def undelete_user(
    user_id: str, db: dbSessionDep, _: CurrentAdmin
) -> BaseResponse:

    return await user_service.undelete_user_by_id(user_id, db)


@router.delete("/profile-picture", response_model=BaseResponse)
async def delete_user_pic(current_user: CurrentActiveUser, db: dbSessionDep):
    return await user_service.deleter_user_profile_pic(current_user, db)
