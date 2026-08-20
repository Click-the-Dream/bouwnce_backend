"""Single-query message insert using PostgreSQL RETURNING.

Replaces: db.add(msg) + db.flush() + db.refresh(msg) (3 roundtrips)
With: INSERT ... RETURNING * (1 roundtrip)
"""

from __future__ import annotations

from typing import TYPE_CHECKING
from uuid import UUID as UUID_Type

from sqlalchemy import func, update
from sqlalchemy.dialects.postgresql import insert as pg_insert

from app.models.chat import Conversation, Message

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession


async def insert_message(
    *,
    db: AsyncSession,
    conversation_id: UUID_Type,
    sender_id: UUID_Type,
    recipient_id: UUID_Type,
    body: str,
    reply_to_message_id: UUID_Type | None = None,
    media_type: str | None = None,
    media_urls: list[str] | None = None,
    media_name: str | None = None,
) -> Message:
    """Insert a message in ONE roundtrip (no flush, no refresh)."""
    stmt = (
        pg_insert(Message)
        .values(
            conversation_id=conversation_id,
            sender_id=sender_id,
            recipient_id=recipient_id,
            body=body,
            reply_to_message_id=reply_to_message_id,
            media_type=media_type,
            media_urls=media_urls,
            media_name=media_name,
        )
        .returning(Message)
    )
    result = await db.execute(stmt)
    return result.scalar_one()
