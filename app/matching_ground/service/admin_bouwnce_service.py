from __future__ import annotations

from fastapi import status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.matching_ground.service.bouwnce_dm_service import bouwnce_dm_service
from app.matching_ground.service.chat_service import chat_service
from app.models.user import User
from app.utils.exception import BadRequestException, NotFoundException
from app.utils.responses import response_builder


class AdminBouwnceService:
    async def send_message(
        self,
        *,
        db: AsyncSession,
        redis,
        user_ids: list[str],
        body: str,
        commit: bool = True,
    ) -> dict:
        system_user = await bouwnce_dm_service.get_system_user(db=db)
        if system_user is None:
            raise BadRequestException("Bouwnce system user not found or not configured")

        # Validate users exist (strict).
        for uid in user_ids:
            exists = (
                await db.execute(select(User.id).where(User.id == uid))
            ).scalar_one_or_none()
            if exists is None:
                raise NotFoundException(f"User not found: {uid}")

        sent: list[dict] = []
        for uid in user_ids:
            await bouwnce_dm_service.ensure_welcome_conversation(
                db=db, redis=redis, user_id=str(uid), commit=False
            )
            result = await chat_service.send_message(
                db=db,
                redis=redis,
                sender=system_user,
                recipient_id=str(uid),
                body=body,
                commit=False,
                as_response=False,
            )
            sent.append(
                {
                    "user_id": str(uid),
                    "conversation_id": result["conversation_id"],
                    "message_id": result["message"]["id"],
                }
            )

        if commit:
            await db.commit()

        return response_builder(
            status_code=status.HTTP_201_CREATED,
            status="success",
            message="Bouwnce messages sent",
            data={"items": sent, "count": len(sent)},
        )


admin_bouwnce_service = AdminBouwnceService()
