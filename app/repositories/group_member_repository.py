"""
Group Member Repository
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import select, update
from sqlalchemy.dialects.postgresql import insert as pg_insert

from app.models.chat import GroupMember

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession


class GroupMemberRepository:
    async def add_member(
        self,
        *,
        db: AsyncSession,
        group_id: str,
        user_id: str,
        role: str = "member",
        invited_by: str | None = None,
    ) -> GroupMember | None:
        """Add a user to a group. Returns None if user is already a member."""
        # Check if user is already a member
        existing = await self.get_member(db, group_id, user_id)
        if existing:
            return None

        stmt = (
            pg_insert(GroupMember)
            .values(
                group_id=group_id,
                user_id=user_id,
                role=role,
                invited_by=invited_by,
            )
            .returning(GroupMember)
        )
        result = await db.execute(stmt)
        return result.scalar_one()

    async def remove_member(
        self, db: AsyncSession, group_id: str, user_id: str
    ) -> bool:
        """Remove a user from a group."""
        member = await self.get_member(db, group_id, user_id)
        if not member:
            return False

        stmt = (
            update(GroupMember)
            .where(GroupMember.id == member.id)
            .values(is_active=False)
        )
        await db.execute(stmt)
        return True

    async def get_member(
        self, db: AsyncSession, group_id: str, user_id: str
    ) -> GroupMember | None:
        """Get a specific member of a group."""
        result = await db.execute(
            select(GroupMember).where(
                GroupMember.group_id == group_id,
                GroupMember.user_id == user_id,
                GroupMember.is_active.is_(True),
            )
        )
        return result.scalar_one_or_none()

    async def get_group_members(
        self, db: AsyncSession, group_id: str, include_inactive: bool = False
    ) -> list[GroupMember]:
        """Get all members of a group."""
        query = select(GroupMember).where(GroupMember.group_id == group_id)

        if not include_inactive:
            query = query.where(GroupMember.is_active.is_(True))

        result = await db.execute(query.order_by(GroupMember.joined_at.asc()))
        return list(result.scalars().all())

    async def get_user_role_in_group(
        self, db: AsyncSession, group_id: str, user_id: str
    ) -> str | None:
        """Get a user's role in a specific group."""
        member = await self.get_member(db, group_id, user_id)
        return member.role if member else None

    async def update_member_role(
        self,
        *,
        db: AsyncSession,
        group_id: str,
        user_id: str,
        role: str,
    ) -> bool:
        """Update a member's role in a group."""
        member = await self.get_member(db, group_id, user_id)
        if not member:
            return False

        stmt = update(GroupMember).where(GroupMember.id == member.id).values(role=role)
        await db.execute(stmt)
        return True

    async def transfer_ownership(
        self,
        *,
        db: AsyncSession,
        group_id: str,
        new_owner_id: str,
        current_owner_id: str,
    ) -> bool:
        """Transfer group ownership to another member."""
        # Verify current owner
        current_member = await self.get_member(db, group_id, current_owner_id)
        if not current_member or current_member.role != "owner":
            return False

        # Verify new owner is a member
        new_member = await self.get_member(db, group_id, new_owner_id)
        if not new_member:
            return False

        # Transfer ownership
        await self.update_member_role(
            db=db, group_id=group_id, user_id=current_owner_id, role="admin"
        )
        await self.update_member_role(
            db=db, group_id=group_id, user_id=new_owner_id, role="owner"
        )

        return True
