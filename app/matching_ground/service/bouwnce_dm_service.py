from __future__ import annotations

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.matching_ground.service.chat_service import chat_service
from app.models.chat import Message
from app.models.user import User


class BouwnceDMService:
    async def get_system_user(self, *, db: AsyncSession) -> User | None:
        if settings.BOUWNCE_SYSTEM_EMAIL:
            by_email = (
                await db.execute(
                    select(User).where(User.email == settings.BOUWNCE_SYSTEM_EMAIL)
                )
            ).scalar_one_or_none()
            if by_email is not None:
                return by_email

        if settings.BOUWNCE_SYSTEM_USERNAME:
            by_username = (
                await db.execute(
                    select(User).where(
                        User.username == settings.BOUWNCE_SYSTEM_USERNAME
                    )
                )
            ).scalar_one_or_none()
            if by_username is not None:
                return by_username

        if settings.BOUWNCE_SYSTEM_FULL_NAME:
            by_name = (
                await db.execute(
                    select(User).where(
                        User.full_name == settings.BOUWNCE_SYSTEM_FULL_NAME
                    )
                )
            ).scalar_one_or_none()
            if by_name is not None:
                return by_name

        return None

    async def ensure_welcome_conversation(
        self,
        *,
        db: AsyncSession,
        redis,
        user_id: str,
        commit: bool = False,
    ) -> None:
        system_user = await self.get_system_user(db=db)
        if system_user is None:
            return

        if str(system_user.id) == str(user_id):
            return

        role = (
            await db.execute(select(User.role).where(User.id == user_id))
        ).scalar_one_or_none()
        if role == "admin":
            return

        conversation = await chat_service.get_or_create_conversation(
            db=db, user1_id=str(system_user.id), user2_id=str(user_id)
        )

        existing_stmt = (
            select(func.count())
            .select_from(Message)
            .where(Message.conversation_id == conversation.id)
        )
        existing = int((await db.execute(existing_stmt)).scalar() or 0)
        if existing > 0:
            return

        welcome = (getattr(settings, "BOUWNCE_WELCOME_MESSAGE", "") or "").strip()
        if not welcome:
            return

        await chat_service.send_message(
            db=db,
            redis=redis,
            sender=system_user,
            recipient_id=str(user_id),
            body=welcome,
            commit=False,
            as_response=False,
        )
        if commit:
            await db.commit()


bouwnce_dm_service = BouwnceDMService()
