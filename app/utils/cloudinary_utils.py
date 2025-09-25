import asyncio
import os
import tempfile
from concurrent.futures import ThreadPoolExecutor
from typing import Any

import cloudinary
import cloudinary.api
import cloudinary.uploader
from fastapi import UploadFile

from app.core.config import settings

executor = ThreadPoolExecutor()


cloudinary.config(
    cloud_name=settings.CLOUDINARY_NAME,
    api_key=settings.CLOUDINARY_KEY,
    api_secret=settings.CLOUDINARY_SECRET,
    secure=True,
)


async def upload_image(path: str, folder_name: str) -> dict[str, Any]:
    try:
        loop = asyncio.get_event_loop()

        result = await loop.run_in_executor(
            executor, lambda: cloudinary.uploader.upload(path, folder=folder_name)
        )
        return {"url": result["secure_url"], "public_id": result["public_id"]}
    except Exception as e:
        print(f"Error uploading image {path}: {str(e)}")
        return None


async def upload_images(file_paths: list[str], folder_name) -> list[dict[str, Any]]:
    try:
        task = [upload_image(path, folder_name) for path in file_paths]

        return await asyncio.gather(*task)
    except Exception as e:
        print("Error uploading multiple images: ", str(e))
        return None


def delete_images(public_ids: list[str]) -> bool:
    try:
        cloudinary.api.delete_resources(public_ids)
        return True
    except Exception as e:
        print("Error delete images: ", str(e))
        return False


def delete_folder(folder_name: str) -> bool:
    try:
        cloudinary.api.delete_resources_by_prefix(f"/{folder_name}")
        return True
    except Exception as e:
        print(f"Error deleting folder {folder_name}: ", str(e))
        return False


async def save_uploaded_file_temp(uploads: list[UploadFile]) -> list[str]:

    temp_paths = []

    for upload in uploads:
        suffix = os.path.splitext(upload.filename)[1]
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as temp:
            content = await upload.read()
            temp.write(content)
            temp_path = temp.name
            temp_paths.append(temp_path)

        await upload.close()

    return temp_paths
