"""Chat serialization utilities and lightweight user loaders.

Extracted from chat_service.py to keep file sizes manageable.
"""

from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from app.matching_ground.schema.chat import (
    ChatMessageData,
    ChatMessageEvent,
)
from app.models.chat import Conversation
from app.models.user import User


class ChatSerializers:
    """Serialization helpers and batch user loaders."""

    @staticmethod
    def _extract_profile_pic_url(user: User) -> str | None:
        value = getattr(user, "profile_pic", None)
        if not value:
            return None
        if isinstance(value, str):
            return value
        if isinstance(value, dict):
            url_val = value.get("url")
            if isinstance(url_val, str):
                return url_val
            if isinstance(url_val, dict):
                nested = url_val.get("url")
                return nested if isinstance(nested, str) else None
        return None

    @staticmethod
    def _serialize_profile_pic(user: User) -> dict | None:
        url = ChatSerializers._extract_profile_pic_url(user)
        if not url:
            return None
        return {"url": url}

    @staticmethod
    def _serialize_user(user: User) -> dict:
        return {
            "id": str(user.id),
            "username": user.username,
            "full_name": user.full_name,
            "profile_pic": ChatSerializers._serialize_profile_pic(user),
        }

    @staticmethod
    def _serialize_conversation(
        conv: Conversation,
        *,
        current_user_id: str,
        users_by_id: dict | None = None,
    ) -> dict:
        """
        API-safe conversation dict including the other participant's identity.

        ``users_by_id`` is an optional pre-fetched lookup so we avoid the
        expensive ``lazy="joined"`` cascade that User's relationships cause.
        """
        base = {
            "id": str(conv.id),
            "user_a_id": str(conv.user_a_id),
            "user_b_id": str(conv.user_b_id),
            "last_message_at": (
                conv.last_message_at.isoformat()
                if getattr(conv, "last_message_at", None)
                else None
            ),
            "created_at": conv.created_at.isoformat() if conv.created_at else None,
            "updated_at": conv.updated_at.isoformat() if conv.updated_at else None,
        }

        current_id = str(current_user_id)
        other_id = (
            str(conv.user_b_id)
            if current_id == str(conv.user_a_id)
            else str(conv.user_a_id)
        )
        if users_by_id is not None:
            other = users_by_id.get(other_id)
        else:
            other = conv.user_b if current_id == str(conv.user_a_id) else conv.user_a
        base["user"] = {
            "id": str(other.id),
            "username": other.username,
            "full_name": other.full_name,
            "profile_pic": ChatSerializers._serialize_profile_pic(other),
        }
        return base

    @staticmethod
    async def _load_users_for_conversations(
        db: AsyncSession, conversations: list[Conversation]
    ) -> dict[str, User]:
        """Batch-load lightweight users referenced by *conversations*.

        Returns a ``{user_id_str: User}`` lookup dict.
        """
        user_ids: set[str] = set()
        for conv in conversations:
            user_ids.add(str(conv.user_a_id))
            user_ids.add(str(conv.user_b_id))
        if not user_ids:
            return {}
        users = await User.get_chat_users_by_ids(list(user_ids), db)
        return {str(u.id): u for u in users}

    @staticmethod
    async def _load_two_conversation_users(
        db: AsyncSession, conv: Conversation
    ) -> dict[str, User]:
        """Load only the two participants for a single conversation."""
        user_ids = [str(conv.user_a_id), str(conv.user_b_id)]
        users = await User.get_chat_users_by_ids(user_ids, db)
        return {str(u.id): u for u in users}

    def _build_chat_message_data(
        self,
        *,
        msg,
        sender: User,
        recipient: User,
        reply_obj: dict | bool,
    ) -> ChatMessageData:
        message_payload = msg.to_dict()
        message_payload["sender"] = self._serialize_user(sender)
        message_payload["recipient"] = self._serialize_user(recipient)
        message_payload["reply_to_message"] = reply_obj
        return ChatMessageData.model_validate(message_payload)

    def _build_chat_message_event(
        self,
        *,
        msg,
        sender: User,
        recipient: User,
        reply_obj: dict | bool,
    ) -> ChatMessageEvent:
        return ChatMessageEvent(
            data=self._build_chat_message_data(
                msg=msg,
                sender=sender,
                recipient=recipient,
                reply_obj=reply_obj,
            )
        )
