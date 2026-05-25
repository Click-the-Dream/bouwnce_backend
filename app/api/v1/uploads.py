from __future__ import annotations

from enum import Enum

from fastapi import APIRouter, status
from pydantic import BaseModel, Field

from app.api.dependencies import CurrentActiveUser
from app.core.config import settings
from app.service.upload_service import upload_service
from app.utils.responses import response_builder

router = APIRouter(prefix="/uploads", tags=["Uploads"])


class UploadType(Enum):
    image = "image"
    video = "video"
    file = "file"


class ChatSignRequest(BaseModel):
    upload_type: UploadType = Field(..., description="image|video|file")
    count: int = Field(
        1, ge=1, le=50, description="How many signed uploads to generate"
    )
    file_name: str | None = Field(
        None,
        max_length=255,
        description="Optional file name to incorporate into Cloudinary public_id",
    )


def _preset_for(upload_type: UploadType) -> str:
    if upload_type == UploadType.image:
        return settings.CHAT_IMAGES_PRESET
    if upload_type == UploadType.video:
        return settings.CHAT_VIDEOS_PRESET
    return settings.CHAT_FILES_PRESET


def _constraints_for(upload_type: UploadType) -> dict:
    if upload_type == UploadType.image:
        return upload_service.chat_image_constraints()
    if upload_type == UploadType.video:
        return upload_service.chat_video_constraints()
    return upload_service.chat_file_constraints()


@router.post(
    "/chat/sign",
    summary="Get signed Cloudinary params for chat uploads (image/video/file)",
    status_code=status.HTTP_200_OK,
    response_model=dict,
)
async def sign_chat_upload(
    payload: ChatSignRequest, current_user: CurrentActiveUser
) -> dict:
    folder = f"chat/{current_user.id}"
    constraints = _constraints_for(payload.upload_type)
    preset = _preset_for(payload.upload_type)

    if payload.count == 1:
        fields = upload_service.sign_chat_upload(
            preset=preset, folder=folder, file_name=payload.file_name
        )
        data = {
            "upload_type": payload.upload_type,
            "fields": fields,
            "constraints": constraints,
        }
        message = "Chat upload signature generated"
    else:
        items = upload_service.sign_chat_upload_batch(
            preset=preset, folder=folder, count=payload.count
        )
        data = {
            "upload_type": payload.upload_type,
            "count": len(items),
            "items": items,
            "constraints": constraints,
        }
        message = "Chat upload signatures generated"

    return response_builder(
        status_code=status.HTTP_200_OK,
        status="success",
        message=message,
        data=data,
    )
