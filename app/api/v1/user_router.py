from fastapi import APIRouter

from app.api.dependencies import CurrentAdmin, CurrentUser, dbSessionDep
from app.schemas.user import UpdateUser, UserResponse
from app.service.user_service import user_service

router = APIRouter(prefix="/users", tags=["User"])


@router.get("/me", summary="Get current user", response_model=UserResponse)
async def get_me(current_user: CurrentUser, db: dbSessionDep) -> UserResponse:

    return await user_service.get_me(current_user)


@router.get("/{user_id}", summary="Get user by ID", response_model=UserResponse)
async def get_user_by_id(
    user_id: str, db: dbSessionDep, _: CurrentUser
) -> UserResponse:

    return await user_service.get_user_by_id(user_id, db)


@router.get(
    "/",
    summary="List users with search and pagination",
    response_model=list[UserResponse],
)
async def list_users(
    db: dbSessionDep,
    _: CurrentUser,
    page: int = 1,
    page_size: int = 10,
    search: str | None = None,
) -> list[UserResponse]:

    return await user_service.list_users(db, search, page, page_size)


@router.put("/me", summary="Update current user", response_model=UserResponse)
async def update_me(
    user_data: UpdateUser, current_user: CurrentUser, db: dbSessionDep
) -> UserResponse:
    user_data = user_data.model_dump(exclude_unset=True)
    if user_data.get("role", None) is not None:
        user_data["role"] = user_data["role"].value
    return await user_service.update_me(current_user, user_data, db)


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


@router.delete("/me", summary="Delete current user", response_model=UserResponse)
async def delete_me(current_user: CurrentUser, db: dbSessionDep) -> UserResponse:

    return await user_service.delete_me(current_user, db)


@router.delete(
    "/{user_id}", summary="Delete user by ID, only admin", response_model=UserResponse
)
async def delete_user(_: CurrentAdmin, user_id: str, db: dbSessionDep) -> UserResponse:

    return await user_service.delete_user_by_id(user_id, db)


@router.post(
    "/undelete/{user_id}",
    summary="Undelete user by ID, only admin",
    response_model=UserResponse,
)
async def undelete_user(
    user_id: str, db: dbSessionDep, _: CurrentAdmin
) -> UserResponse:

    return await user_service.undelete_user_by_id(user_id, db)
