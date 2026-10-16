"""
Group Message Repository
"""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import desc, func, select, text, update
from sqlalchemy.dialects.postgresql import insert as pg_insert

from app.models.chat import GroupMessage, GroupMessageDeletion

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession


class GroupMessageRepository:
    async def create_message(
        self,
        *,
        db: AsyncSession,
        group_id: str,
        sender_id: str,
        body: str,
        media_type: str | None = None,
        media_urls: list[str] | None = None,
        media_names: list[str] | None = None,
        reply_to_message_id: str | None = None,
        mentioned_user_ids: list[str] | None = None,
    ) -> GroupMessage:
        """Create a new group message."""
        stmt = (
            pg_insert(GroupMessage)
            .values(
                group_id=group_id,
                sender_id=sender_id,
                body=body,
                media_type=media_type,
                media_urls=media_urls,
                media_names=media_names,
                reply_to_message_id=reply_to_message_id,
                mentioned_user_ids=(
                    [str(uid) for uid in mentioned_user_ids]
                    if mentioned_user_ids is not None
                    else None
                ),
            )
            .returning(GroupMessage)
        )
        result = await db.execute(stmt)
        return result.scalar_one()

    async def get_message_by_id(
        self, db: AsyncSession, message_id: str
    ) -> GroupMessage | None:
        """Get group message by ID."""
        return await GroupMessage.get_by_id(str(message_id), db)

    async def get_group_messages(
        self,
        *,
        db: AsyncSession,
        group_id: str,
        page: int = 1,
        page_size: int = 50,
        before_message_id: str | None = None,
        user_id: str | None = None,
    ) -> tuple[list[GroupMessage], int]:
        """Get messages for a group with pagination."""
        query = select(GroupMessage).where(GroupMessage.group_id == group_id)
        total_query = (
            select(func.count())
            .select_from(GroupMessage)
            .where(GroupMessage.group_id == group_id)
        )
        if user_id is not None:
            visible_to_user = (
                ~select(GroupMessageDeletion.id)
                .where(
                    GroupMessageDeletion.message_id == GroupMessage.id,
                    GroupMessageDeletion.user_id == user_id,
                )
                .exists()
            )
            query = query.where(visible_to_user)
            total_query = total_query.where(visible_to_user)

        # If we have a before_message_id, get messages before that point
        if before_message_id:
            before_msg = await self.get_message_by_id(db, before_message_id)
            if before_msg:
                query = query.where(GroupMessage.created_at < before_msg.created_at)
                total_query = total_query.where(
                    GroupMessage.created_at < before_msg.created_at
                )

        total_result = await db.execute(total_query)
        total = total_result.scalar() or 0

        # Get paginated results
        result = await db.execute(
            query.order_by(desc(GroupMessage.created_at))
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
        messages = list(result.scalars().all())

        return messages, total

    async def get_unread_count(
        self, db: AsyncSession, group_id: str, user_id: str
    ) -> int:
        """Get unread message count for a user in a group.

        Note: This is a simplified implementation. For production, you might want
        to track read receipts per user rather than a global read count.
        """
        # For now, we'll use a simplified approach
        # In a full implementation, you'd have a GroupMessageRead table
        # tracking which users have read which messages

        # Placeholder: a real implementation would query a per-user read
        # receipt table (GroupMessageRead) instead of returning a constant.
        return 0  # Simplified - in reality, you'd check actual read status

    async def mark_messages_as_read(
        self,
        *,
        db: AsyncSession,
        group_id: str,
        user_id: str,
        message_ids: list[str] | None = None,
    ) -> int:
        """Mark messages as read for a user.

        Note: This is a placeholder implementation. For a complete solution,
        you would need a GroupMessageRead table to track per-user read status.
        """
        # Placeholder implementation
        # Real implementation would insert/update records in GroupMessageRead table
        return 0

    async def get_mentioned_messages(
        self, db: AsyncSession, user_id: str, limit: int = 50
    ) -> list[GroupMessage]:
        """Get messages where a user was mentioned."""
        # This requires checking the JSONB array for the user_id
        # Postgresql syntax for checking if value exists in JSON array
        result = await db.execute(
            select(GroupMessage)
            .where(
                GroupMessage.mentioned_user_ids.isnot(None),
                ~select(GroupMessageDeletion.id)
                .where(
                    GroupMessageDeletion.message_id == GroupMessage.id,
                    GroupMessageDeletion.user_id == user_id,
                )
                .exists(),
                # JSONB ``?`` checks for a matching string element in the array
                text("mentioned_user_ids ? :user_id"),
            )
            .params(user_id=str(user_id))
            .order_by(desc(GroupMessage.created_at))
            .limit(limit)
        )
        return list(result.scalars().all())

    async def update_message(
        self,
        *,
        db: AsyncSession,
        message_id: str,
        body: str | None = None,
        media_type: str | None = None,
        media_urls: list[str] | None = None,
        media_names: list[str] | None = None,
        sender_id: str | None = None,
        edited_after: datetime | None = None,
    ) -> GroupMessage | None:
        """Update a group message."""
        message = await self.get_message_by_id(db, message_id)
        if not message:
            return None

        update_data = {}
        if body is not None:
            update_data["body"] = body
        if media_type is not None:
            update_data["media_type"] = media_type
        if media_urls is not None:
            update_data["media_urls"] = media_urls
        if media_names is not None:
            update_data["media_names"] = media_names
        if (
            body is not None
            or media_type is not None
            or media_urls is not None
            or media_names is not None
        ):
            update_data["edited_at"] = func.now()
            update_data["is_edited"] = True

        if update_data:
            stmt = (
                update(GroupMessage)
                .where(
                    GroupMessage.id == message_id,
                    GroupMessage.deleted_for_everyone_at.is_(None),
                )
                .values(**update_data)
            )
            if sender_id is not None:
                stmt = stmt.where(GroupMessage.sender_id == sender_id)
            if edited_after is not None:
                stmt = stmt.where(GroupMessage.created_at >= edited_after)
            stmt = stmt.returning(GroupMessage)
            result = await db.execute(stmt)
            updated_message = result.scalar_one_or_none()
            if updated_message is None:
                return None
            # ``get_message_by_id`` above already put this PK in the identity
            # map, so the RETURNING row resolves to that (stale) instance.
            await db.refresh(updated_message)
            return updated_message

        return message

    async def delete_for_user(
        self, db: AsyncSession, message_id: str, user_id: str
    ) -> None:
        stmt = (
            pg_insert(GroupMessageDeletion)
            .values(message_id=message_id, user_id=user_id)
            .on_conflict_do_nothing(index_elements=["message_id", "user_id"])
        )
        await db.execute(stmt)

    async def delete_for_everyone(
        self,
        db: AsyncSession,
        message_id: str,
        sender_id: str,
        delete_after: datetime,
    ) -> GroupMessage | None:
        stmt = (
            update(GroupMessage)
            .where(
                GroupMessage.id == message_id,
                GroupMessage.sender_id == sender_id,
                GroupMessage.created_at >= delete_after,
                GroupMessage.deleted_for_everyone_at.is_(None),
            )
            .values(
                body="This message was deleted",
                media_type=None,
                media_urls=None,
                media_names=None,
                mentioned_user_ids=None,
                deleted_for_everyone_at=func.now(),
            )
            .returning(GroupMessage)
        )
        result = await db.execute(stmt)
        message = result.scalar_one_or_none()
        if message is not None:
            await db.refresh(message)
        return message
