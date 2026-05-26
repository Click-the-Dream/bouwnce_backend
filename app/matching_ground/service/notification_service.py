from __future__ import annotations

import uuid
from datetime import UTC, datetime

from fastapi import status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.matching_ground.model.notification import Notification
from app.utils.exception import ForbiddenException, NotFoundException
from app.utils.responses import response_builder


class NotificationService:
    async def list_for_user(
        self,
        *,
        db: AsyncSession,
        user_id: str,
        page: int = 1,
        page_size: int = 20,
        as_response: bool = True,
    ) -> dict:
        offset = (page - 1) * page_size
        stmt = (
            select(Notification)
            .where(Notification.user_id == uuid.UUID(str(user_id)))
            .order_by(Notification.created_at.desc())
            .offset(offset)
            .limit(page_size)
        )
        rows = list((await db.execute(stmt)).scalars().all())

        data = {
            "items": [n.to_dict() for n in rows],
            "page": page,
            "page_size": page_size,
            "total": len(rows),
        }
        if as_response:
            return response_builder(
                status_code=status.HTTP_200_OK,
                status="success",
                message="Notifications fetched successfully",
                data=data,
            )
        return data

    async def mark_read(
        self,
        *,
        db: AsyncSession,
        user_id: str,
        notification_id: str,
        as_response: bool = True,
    ) -> dict:
        try:
            nid = uuid.UUID(str(notification_id))
        except Exception:
            raise NotFoundException("Notification not found") from None

        notif = (
            await db.execute(select(Notification).where(Notification.id == nid))
        ).scalar_one_or_none()
        if notif is None:
            raise NotFoundException("Notification not found")
        if str(notif.user_id) != str(user_id):
            raise ForbiddenException("You cannot modify this notification")

        if notif.read_at is None:
            notif.read_at = datetime.now(UTC)
            await notif.save(db)

        data = {"id": str(notif.id), "read": bool(notif.read_at)}
        if as_response:
            return response_builder(
                status_code=status.HTTP_200_OK,
                status="success",
                message="Notification marked as read",
                data=data,
            )
        return data


notification_service = NotificationService()
