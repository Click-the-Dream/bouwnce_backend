from __future__ import annotations

from fastapi import APIRouter, status

from app.api.dependencies import CurrentActiveUser
from app.core.config import settings
from app.service.upload_service import upload_service
from app.utils.responses import response_builder

router = APIRouter(prefix="/uploads", tags=["Uploads"])


@router.post(
    "/chat-image/sign",
    summary="Get signed Cloudinary params for chat image upload",
    status_code=status.HTTP_200_OK,
    response_model=dict,
)
async def sign_chat_image_upload(current_user: CurrentActiveUser) -> dict:
    folder = f"chat/{current_user.id}"
    signed = upload_service.sign_chat_upload(
        preset=settings.CHAT_IMAGES_PRESET, folder=folder
    )
    return response_builder(
        status_code=status.HTTP_200_OK,
        status="success",
        message="Chat image upload signature generated",
        data={
            **signed,
            "constraints": upload_service.chat_image_constraints(),
        },
    )


@router.post(
    "/chat-video/sign",
    summary="Get signed Cloudinary params for chat video upload",
    status_code=status.HTTP_200_OK,
    response_model=dict,
)
async def sign_chat_video_upload(current_user: CurrentActiveUser) -> dict:
    folder = f"chat/{current_user.id}"
    signed = upload_service.sign_chat_upload(
        preset=settings.CHAT_VIDEOS_PRESET, folder=folder
    )
    return response_builder(
        status_code=status.HTTP_200_OK,
        status="success",
        message="Chat video upload signature generated",
        data={
            **signed,
            "constraints": upload_service.chat_video_constraints(),
        },
    )


@router.post(
    "/chat-file/sign",
    summary="Get signed Cloudinary params for chat file upload",
    status_code=status.HTTP_200_OK,
    response_model=dict,
)
async def sign_chat_file_upload(current_user: CurrentActiveUser) -> dict:
    folder = f"chat/{current_user.id}"
    signed = upload_service.sign_chat_upload(
        preset=settings.CHAT_FILES_PRESET, folder=folder
    )
    return response_builder(
        status_code=status.HTTP_200_OK,
        status="success",
        message="Chat file upload signature generated",
        data={
            **signed,
            "constraints": upload_service.chat_file_constraints(),
        },
    )
