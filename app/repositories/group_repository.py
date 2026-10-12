"""
Group Chat Repository
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import func, select, update
from sqlalchemy.dialects.postgresql import insert as pg_insert

from app.models.chat import Group, GroupMember

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession


class GroupRepository:
    async def create_group(
        self,
        *,
        db: AsyncSession,
        name: str,
        created_by: str,
        description: str | None = None,
    ) -> Group:
        """Create a new group."""
        stmt = (
            pg_insert(Group)
            .values(
                name=name,
                description=description,
                created_by=created_by,
            )
            .returning(Group)
        )
        result = await db.execute(stmt)
        return result.scalar_one()

    async def get_group_by_id(self, db: AsyncSession, group_id: str) -> Group | None:
        """Get group by ID."""
        return await Group.get_by_id(str(group_id), db)

    async def get_group_by_name(self, db: AsyncSession, name: str) -> Group | None:
        """Get group by name."""
        result = await db.execute(
            select(Group).where(Group.name == name, Group.is_active.is_(True))
        )
        return result.scalar_one_or_none()

    async def get_user_groups(
        self, db: AsyncSession, user_id: str, include_inactive: bool = False
    ) -> list[Group]:
        """Get all groups for a user."""
        query = (
            select(Group)
            .join(GroupMember)
            .where(
                GroupMember.user_id == user_id,
                GroupMember.is_active.is_(True),
                Group.is_active.is_(True),
            )
        )

        if not include_inactive:
            query = query.where(Group.is_active.is_(True))

        result = await db.execute(query.order_by(Group.updated_at.desc()))
        return list(result.scalars().all())

    async def update_group(
        self,
        *,
        db: AsyncSession,
        group_id: str,
        name: str | None = None,
        description: str | None = None,
        is_active: bool | None = None,
    ) -> Group | None:
        """Update group properties."""
        group = await self.get_group_by_id(db, group_id)
        if not group:
            return None

        update_data = {}
        if name is not None:
            update_data["name"] = name
        if description is not None:
            update_data["description"] = description
        if is_active is not None:
            update_data["is_active"] = is_active

        if update_data:
            update_data["updated_at"] = func.now()
            stmt = (
                update(Group)
                .where(Group.id == group_id)
                .values(**update_data)
                .returning(Group)
            )
            result = await db.execute(stmt)
            updated_group = result.scalar_one()
            # ``get_group_by_id`` above already put this PK in the identity map,
            # so the RETURNING row resolves to that (stale) instance. Reload it.
            await db.refresh(updated_group)
            return updated_group

        return group

    async def delete_group(self, db: AsyncSession, group_id: str) -> bool:
        """Soft delete group by setting is_active=False."""
        group = await self.get_group_by_id(db, group_id)
        if not group:
            return False

        stmt = (
            update(Group)
            .where(Group.id == group_id)
            .values(is_active=False, updated_at=func.now())
        )
        await db.execute(stmt)
        return True
