from __future__ import annotations

import time
from uuid import uuid4

from cloudinary.utils import api_sign_request

from app.core.config import settings
from app.utils.upload_utils import safe_slug_from_filename, split_csv


class UploadService:
    @staticmethod
    def sign_chat_upload(*, preset: str, folder: str, file_name: str | None = None) -> dict:
        timestamp = int(time.time())
        slug = safe_slug_from_filename(file_name or "")
        public_id = f"{uuid4()}_{slug}" if slug else str(uuid4())

        params_to_sign = {
            "timestamp": timestamp,
            "folder": folder,
            "public_id": public_id,
            "upload_preset": preset,
        }
        signature = api_sign_request(params_to_sign, settings.CLOUDINARY_SECRET)
        return {
            "cloud_name": settings.CLOUDINARY_NAME,
            "api_key": settings.CLOUDINARY_KEY,
            "timestamp": timestamp,
            "signature": signature,
            "upload_preset": preset,
            "folder": folder,
            "public_id": public_id,
        }

    @classmethod
    def sign_chat_upload_batch(
        cls, *, preset: str, folder: str, count: int
    ) -> list[dict]:
        safe_count = max(1, min(int(count), 50))
        return [
            cls.sign_chat_upload(preset=preset, folder=folder)
            for _ in range(safe_count)
        ]

    @staticmethod
    def chat_image_constraints() -> dict:
        return {
            "max_bytes": settings.CHAT_IMAGES_MAX_BYTES,
            "allowed_formats": split_csv(settings.CHAT_IMAGES_ALLOWED_FORMATS),
            "resource_type": "image",
        }

    @staticmethod
    def chat_video_constraints() -> dict:
        return {
            "max_bytes": settings.CHAT_VIDEOS_MAX_BYTES,
            "allowed_formats": split_csv(settings.CHAT_VIDEOS_ALLOWED_FORMATS),
            "resource_type": "video",
        }

    @staticmethod
    def chat_file_constraints() -> dict:
        return {
            "max_bytes": settings.CHAT_FILES_MAX_BYTES,
            "allowed_formats": split_csv(settings.CHAT_FILES_ALLOWED_FORMATS),
            "resource_type": "raw",
        }


upload_service = UploadService()
