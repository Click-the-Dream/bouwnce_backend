from typing import Any

from fastapi import APIRouter, BackgroundTasks, status

from app.api.dependencies import (
    CurrentUser,
    TokenDep,
    dbSessionDep,
    redisSessionDep,
)
from app.schemas.user import CodeVerification, LoginUser, UserCreate, UserResponse
from app.service.auth_service import auth_service

router = APIRouter(tags=["Authentication"], prefix="/auth")


@router.post(
    "/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED
)
async def register_user(
    user_data: UserCreate, background_taks: BackgroundTasks, db: dbSessionDep
):
    user_data_dict = user_data.model_dump()
    user_data_dict["role"] = user_data.role.value

    return await auth_service.create_user(
        user_data_dict, db=db, background_tasks=background_taks
    )


@router.post(
    "/verify-code", status_code=status.HTTP_200_OK, response_model=UserResponse
)
async def verify_code(
    code_data: CodeVerification,
    db: dbSessionDep,
):
    return await auth_service.verify_code(code_data.model_dump(), db)


@router.post("/login", status_code=status.HTTP_200_OK, response_model=dict[str, Any])
async def login_user(
    login_data: LoginUser,
    background_tasks: BackgroundTasks,
    db: dbSessionDep,
):
    return await auth_service.login_user(login_data.email, db, background_tasks)


@router.post("/logout", status_code=status.HTTP_200_OK, response_model=dict[str, Any])
async def logout_user(
    auth: TokenDep,
    redis_db: redisSessionDep,
    _: CurrentUser,
):
    return await auth_service.logout_user(auth=auth, redis_db=redis_db)
