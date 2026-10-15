from __future__ import annotations

from typing import Any
from uuid import UUID

from fastapi import status
from sqlalchemy import case, func, literal, select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.event_broadcast.models.attendance import UserEventAttendance
from app.event_broadcast.models.event_group import EventGroup
from app.event_broadcast.models.events import OutingEvent
from app.matching_ground.model.notification import Notification
from app.models.chat import Group, GroupMember
from app.utils.exception import (
    BadRequestException,
    ForbiddenException,
    NotFoundException,
)
from app.utils.responses import response_builder


class EventGroupService:
    @staticmethod
    def _event_group_name(event: OutingEvent) -> str:
        event_id = str(event.id)
        return f"Event: {event.name[:50]} [{event_id}]"

    @staticmethod
    async def _add_membership(
        db: AsyncSession,
        *,
        group_id: str,
        user_id: str,
        invited_by: str,
        role: str = "member",
    ) -> None:
        statement = (
            pg_insert(GroupMember)
            .values(
                group_id=group_id,
                user_id=user_id,
                invited_by=invited_by,
                role=role,
                is_active=True,
            )
            .on_conflict_do_update(
                index_elements=[GroupMember.group_id, GroupMember.user_id],
                set_={
                    "is_active": True,
                    "role": case(
                        (GroupMember.role == "owner", "owner"),
                        else_=role,
                    ),
                },
            )
        )
        await db.execute(statement)

    @classmethod
    async def _backfill_confirmed_attendees(
        cls,
        db: AsyncSession,
        *,
        event_id: str,
        group_id: str,
        host_id: str,
    ) -> None:
        attendee_ids = (
            select(UserEventAttendance.user_id)
            .where(
                UserEventAttendance.event_id == event_id,
                UserEventAttendance.payment_status == "successful",
                UserEventAttendance.attendance_status == "confirmed",
                UserEventAttendance.is_deleted.is_(False),
                UserEventAttendance.user_id != host_id,
            )
            .distinct()
            .subquery()
        )
        attendees = select(
            func.gen_random_uuid(),
            literal(group_id),
            attendee_ids.c.user_id,
            literal("member"),
            literal(host_id),
            literal(True),
            func.now(),
            func.now(),
            func.now(),
            literal(None),
            literal(False),
        )
        statement = pg_insert(GroupMember).from_select(
            [
                "id",
                "group_id",
                "user_id",
                "role",
                "invited_by",
                "is_active",
                "joined_at",
                "created_at",
                "updated_at",
                "deleted_at",
                "is_deleted",
            ],
            attendees,
        )
        statement = statement.on_conflict_do_update(
            index_elements=[GroupMember.group_id, GroupMember.user_id],
            set_={"is_active": True},
        )
        await db.execute(statement)

    @staticmethod
    async def _notify_confirmed_attendees(
        db: AsyncSession,
        *,
        event: OutingEvent,
        group_id: str,
        host_id: str,
    ) -> None:
        attendee_ids = (
            select(UserEventAttendance.user_id)
            .where(
                UserEventAttendance.event_id == event.id,
                UserEventAttendance.payment_status == "successful",
                UserEventAttendance.attendance_status == "confirmed",
                UserEventAttendance.is_deleted.is_(False),
                UserEventAttendance.user_id != host_id,
            )
            .distinct()
            .subquery()
        )
        attendees = select(
            func.gen_random_uuid(),
            attendee_ids.c.user_id,
            literal("Event group is ready"),
            literal(f"The host opened a group chat for {event.name}."),
            literal("event.group.created"),
            func.jsonb_build_object(
                literal("route"),
                literal("group.chat"),
                literal("event_id"),
                literal(str(event.id)),
                literal("group_id"),
                literal(group_id),
            ),
            func.now(),
            func.now(),
            literal(None),
            literal(False),
        )
        statement = pg_insert(Notification).from_select(
            [
                "id",
                "user_id",
                "title",
                "body",
                "event_type",
                "payload",
                "created_at",
                "updated_at",
                "deleted_at",
                "is_deleted",
            ],
            attendees,
        )
        await db.execute(statement)

    @classmethod
    async def create_or_get_for_host(
        cls, *, db: AsyncSession, event_id: str, host_id: str
    ) -> dict[str, Any]:
        try:
            parsed_event_id = UUID(event_id)
        except (TypeError, ValueError):
            raise BadRequestException("Invalid event ID format") from None

        event_result = await db.execute(
            select(OutingEvent)
            .where(
                OutingEvent.id == parsed_event_id,
                OutingEvent.is_deleted.is_(False),
            )
            .with_for_update()
        )
        event = event_result.scalar_one_or_none()
        if event is None:
            raise NotFoundException("Event not found")
        if str(event.creator_id) != str(host_id):
            raise ForbiddenException("Only the event host can create its group")

        link_result = await db.execute(
            select(EventGroup).where(EventGroup.event_id == parsed_event_id)
        )
        link = link_result.scalar_one_or_none()

        created = link is None
        if link is None:
            group_statement = (
                pg_insert(Group)
                .values(
                    name=cls._event_group_name(event),
                    description=f"Chat for event: {event.name}"[:500],
                    created_by=host_id,
                    is_active=True,
                )
                .returning(Group)
            )
            group = (await db.execute(group_statement)).scalar_one()
            link = EventGroup(
                event_id=parsed_event_id,
                group_id=group.id,
                created_by=host_id,
            )
            db.add(link)
            await db.flush()
        else:
            group_result = await db.execute(
                select(Group).where(
                    Group.id == link.group_id,
                    Group.is_active.is_(True),
                    Group.is_deleted.is_(False),
                )
            )
            group = group_result.scalar_one_or_none()
            if group is None:
                raise NotFoundException("The event group is no longer available")

        await cls._add_membership(
            db,
            group_id=str(group.id),
            user_id=host_id,
            invited_by=host_id,
            role="owner",
        )
        await cls._backfill_confirmed_attendees(
            db,
            event_id=str(event.id),
            group_id=str(group.id),
            host_id=str(event.creator_id),
        )
        if created:
            await cls._notify_confirmed_attendees(
                db,
                event=event,
                group_id=str(group.id),
                host_id=str(event.creator_id),
            )
        member_count = await cls._count_members(db, str(group.id))
        return response_builder(
            status_code=status.HTTP_201_CREATED if created else status.HTTP_200_OK,
            message="Event group is ready",
            data={
                "event_id": str(event.id),
                "group": group.to_dict(),
                "member_count": member_count,
                "is_owner": True,
            },
        )

    @staticmethod
    async def _count_members(db: AsyncSession, group_id: str) -> int:
        result = await db.execute(
            select(func.count())
            .select_from(GroupMember)
            .where(GroupMember.group_id == group_id, GroupMember.is_active.is_(True))
        )
        return int(result.scalar_one())

    @classmethod
    async def get_for_attendee(
        cls, *, db: AsyncSession, event_id: str, user_id: str
    ) -> dict[str, Any]:
        try:
            parsed_event_id = UUID(event_id)
        except (TypeError, ValueError):
            raise BadRequestException("Invalid event ID format") from None

        event_result = await db.execute(
            select(OutingEvent).where(
                OutingEvent.id == parsed_event_id,
                OutingEvent.is_deleted.is_(False),
            )
        )
        event = event_result.scalar_one_or_none()
        if event is None:
            raise NotFoundException("Event not found")

        is_host = str(event.creator_id) == str(user_id)
        if not is_host:
            attendance = await db.execute(
                select(UserEventAttendance.id)
                .where(
                    UserEventAttendance.event_id == parsed_event_id,
                    UserEventAttendance.user_id == user_id,
                    UserEventAttendance.payment_status == "successful",
                    UserEventAttendance.attendance_status == "confirmed",
                    UserEventAttendance.is_deleted.is_(False),
                )
                .limit(1)
            )
            if attendance.scalar_one_or_none() is None:
                raise ForbiddenException(
                    "Only the event host and confirmed attendees can access its group"
                )

        result = await db.execute(
            select(EventGroup, Group)
            .join(Group, Group.id == EventGroup.group_id)
            .where(
                EventGroup.event_id == parsed_event_id,
                Group.is_active.is_(True),
                Group.is_deleted.is_(False),
            )
        )
        row = result.one_or_none()
        if row is None:
            raise NotFoundException("The event group has not been created")
        link, group = row
        member_count = await cls._count_members(db, str(group.id))
        return response_builder(
            status_code=status.HTTP_200_OK,
            message="Event group retrieved",
            data={
                "event_id": str(link.event_id),
                "group": group.to_dict(),
                "member_count": member_count,
                "is_owner": is_host,
            },
        )

    @classmethod
    async def add_confirmed_attendee(
        cls, *, db: AsyncSession, event_id: str, user_id: str
    ) -> str | None:
        """Enroll an attendee during ticket confirmation when a group exists."""
        link_result = await db.execute(
            select(EventGroup).where(EventGroup.event_id == event_id)
        )
        link = link_result.scalar_one_or_none()
        if link is None:
            return None
        await cls._add_membership(
            db,
            group_id=str(link.group_id),
            user_id=user_id,
            invited_by=str(link.created_by),
        )
        return str(link.group_id)


event_group_service = EventGroupService()
