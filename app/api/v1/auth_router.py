from fastapi import APIRouter, BackgroundTasks, Depends, Request, Response, status

from app.api.dependencies import (
    CurrentUser,
    TokenDep,
    dbSessionDep,
    redisSessionDep,
)

from app.core.rate_limiter import rate_limiter
from app.schemas.user import (
    CodeVerification,
    LoginUser,
    LoginUserResponse,
    UserCreate,
    UserResponse,
)
from app.service.auth_service import auth_service
from app.utils.responses import BaseResponse

router = APIRouter(tags=["Authentication"], prefix="/auth")


@router.post(
    "/register",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[
        Depends(rate_limiter.rate_limit_dependency(ip_times=10, ip_seconds=60))
    ],
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
    "/verify-code",
    status_code=status.HTTP_200_OK,
    response_model=LoginUserResponse,
    dependencies=[
        Depends(rate_limiter.rate_limit_dependency(ip_times=5, ip_seconds=60))
    ],
)
async def verify_code(
    code_data: CodeVerification, db: dbSessionDep, request: Request, response: Response
):
    return await auth_service.verify_code(
        user_data=code_data.model_dump(), request=request, response=response, db=db
    )


@router.post(
    "/resend-otp",
    status_code=status.HTTP_200_OK,
    response_model=BaseResponse,
    dependencies=[
        Depends(rate_limiter.rate_limit_dependency(ip_times=3, ip_seconds=60))
    ],
)
async def resend_otp(
    login_data: LoginUser,
    background_tasks: BackgroundTasks,
    db: dbSessionDep,
):
    return await auth_service.login_user(login_data.email, db, background_tasks)


@router.post(
    "/login",
    status_code=status.HTTP_200_OK,
    response_model=BaseResponse,
    dependencies=[
        Depends(rate_limiter.rate_limit_dependency(ip_times=3, ip_seconds=60))
    ],
    description="Login user by sending otp to user provided email",
)
async def login_user(
    login_data: LoginUser, background_task: BackgroundTasks, db: dbSessionDep
):
    return await auth_service.login_user(login_data.email, db, background_task)


@router.post("/logout", status_code=status.HTTP_200_OK, response_model=BaseResponse)
async def logout_user(
    auth: TokenDep,
    db: dbSessionDep,
    redis_db: redisSessionDep,
    current_user: CurrentUser,
    request: Request,
    response: Response,
):
    return await auth_service.logout_user(
        user_id=str(current_user.id),
        auth=auth,
        redis_db=redis_db,
        db=db,
        request=request,
        response=response,
    )


@router.post(
    "/refresh-token",
    summary="Refresh Access Token",
    status_code=status.HTTP_200_OK,
    response_model=BaseResponse,
    description="Get a new access token, by using refresh token in request cookies",
)
async def refresh_access_token(db: dbSessionDep, request: Request, response: Response):
    return await auth_service.refresh_access_token(
        request=request, response=response, db=db
    )
