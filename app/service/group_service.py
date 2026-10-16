"""
Group Chat Service
"""

from __future__ import annotations

from typing import Any

from fastapi import status
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User
from app.repositories import (
    GroupMemberRepository,
    GroupMessageRepository,
    GroupRepository,
)
from app.utils.chat_utils import ChatSerializers
from app.utils.exception import (
    BadRequestException,
    ConflictException,
    ForbiddenException,
    InternalServerErrorException,
    NotFoundException,
)
from app.utils.responses import response_builder


class GroupService:
    def __init__(self):
        self.group_repo = GroupRepository()
        self.member_repo = GroupMemberRepository()
        self.message_repo = GroupMessageRepository()

    # ==================== GROUP MANAGEMENT ====================

    async def create_group(
        self,
        *,
        db: AsyncSession,
        name: str,
        created_by: str,
        description: str | None = None,
    ) -> dict[str, Any]:
        """Create a new group."""
        try:
            # Check if group name already exists
            existing_group = await self.group_repo.get_group_by_name(db, name)
            if existing_group:
                raise ConflictException(
                    message=f"Group with name '{name}' already exists"
                )

            # Create the group
            group = await self.group_repo.create_group(
                db=db,
                name=name,
                created_by=created_by,
                description=description,
            )

            # Add the creator as the first member (owner role)
            await self.member_repo.add_member(
                db=db,
                group_id=str(group.id),
                user_id=created_by,
                role="owner",
            )

            await db.commit()

            group_data = group.to_dict()
            group_data["member_count"] = 1
            group_data["is_owner"] = True

            return response_builder(
                status_code=status.HTTP_201_CREATED,
                status="success",
                message="Group created successfully",
                data={
                    "group": group_data,
                    "member_count": 1,
                },
            )
        except Exception as e:
            await db.rollback()
            if isinstance(
                e, (ConflictException, NotFoundException, ForbiddenException)
            ):
                raise e
            raise InternalServerErrorException(message=str(e)) from e

    async def get_group_by_id(
        self, db: AsyncSession, group_id: str, user_id: str | None = None
    ) -> dict[str, Any]:
        """Get group details by ID."""
        try:
            group = await self.group_repo.get_group_by_id(db, group_id)
            if not group:
                raise NotFoundException(message="Group not found")

            # Check if user is a member (if user_id provided)
            if user_id:
                is_member = (
                    await self.member_repo.get_member(db, group_id, user_id) is not None
                )
                if not is_member:
                    raise ForbiddenException(
                        message="You are not a member of this group"
                    )

            # Get member count and list
            members = await self.member_repo.get_group_members(db, group_id)
            member_count = len(members)
            member_list = [
                await User.get_by_id(str(member.user_id), db)
                for member in members
                if member.is_active
            ]
            is_owner = (
                any(
                    m.role == "owner" and str(m.user_id) == str(user_id)
                    for m in members
                    if m.is_active
                )
                if user_id
                else False
            )

            group_data = group.to_dict()
            group_data["member_count"] = member_count
            group_data["is_owner"] = is_owner

            return response_builder(
                status_code=status.HTTP_200_OK,
                status="success",
                message="Group details retrieved",
                data={
                    "group": group_data,
                    "member_count": member_count,
                    "members": [user.to_dict() for user in member_list if user],
                    "is_owner": is_owner,
                },
            )
        except Exception as e:
            if isinstance(e, (NotFoundException, ForbiddenException)):
                raise e
            raise InternalServerErrorException(message=str(e)) from e

    async def get_user_groups(
        self, db: AsyncSession, user_id: str, include_inactive: bool = False
    ) -> dict[str, Any]:
        """Get all groups for a user."""
        try:
            groups = await self.group_repo.get_user_groups(
                db=db, user_id=user_id, include_inactive=include_inactive
            )

            # Get member counts for each group
            group_data = []
            for group in groups:
                members = await self.member_repo.get_group_members(
                    db, str(group.id), include_inactive=False
                )
                is_owner = any(
                    m.role == "owner" and str(m.user_id) == str(user_id)
                    for m in members
                    if m.is_active
                )
                group_dict = group.to_dict()
                group_dict["member_count"] = len(members)
                group_dict["is_owner"] = is_owner
                group_data.append(
                    {
                        "group": group_dict,
                        "member_count": len(members),
                        "is_owner": is_owner,
                    }
                )

            return response_builder(
                status_code=status.HTTP_200_OK,
                status="success",
                message="User groups retrieved",
                data={"groups": group_data, "total_count": len(group_data)},
            )
        except Exception as e:
            raise InternalServerErrorException(message=str(e)) from e

    async def update_group(
        self,
        *,
        db: AsyncSession,
        group_id: str,
        user_id: str,
        name: str | None = None,
        description: str | None = None,
    ) -> dict[str, Any]:
        """Update group details."""
        try:
            # Check if user is owner or admin
            member = await self.member_repo.get_member(db, group_id, user_id)
            if not member or member.role not in ["owner", "admin"]:
                raise ForbiddenException(
                    message="Only group owners and admins can update group details"
                )

            # Check if new name conflicts with existing group
            if name:
                existing_group = await self.group_repo.get_group_by_name(db, name)
                if existing_group and str(existing_group.id) != group_id:
                    raise ConflictException(
                        message=f"Group with name '{name}' already exists"
                    )

            # Update the group
            updated_group = await self.group_repo.update_group(
                db=db,
                group_id=group_id,
                name=name,
                description=description,
            )
            if not updated_group:
                raise NotFoundException(message="Group not found")

            await db.commit()

            members = await self.member_repo.get_group_members(db, group_id)
            group_data = updated_group.to_dict()
            group_data["member_count"] = sum(1 for m in members if m.is_active)
            group_data["is_owner"] = member.role == "owner"

            return response_builder(
                status_code=status.HTTP_200_OK,
                status="success",
                message="Group updated successfully",
                data={"group": group_data},
            )
        except Exception as e:
            await db.rollback()
            if isinstance(
                e, (NotFoundException, ForbiddenException, ConflictException)
            ):
                raise e
            raise InternalServerErrorException(message=str(e)) from e

    async def delete_group(
        self, db: AsyncSession, group_id: str, user_id: str
    ) -> dict[str, Any]:
        """Delete a group (soft delete)."""
        try:
            # Check if user is owner
            member = await self.member_repo.get_member(db, group_id, user_id)
            if not member or member.role != "owner":
                raise ForbiddenException(
                    message="Only group owners can delete the group"
                )

            # Delete the group
            success = await self.group_repo.delete_group(db, group_id)
            if not success:
                raise NotFoundException(message="Group not found")

            await db.commit()

            return response_builder(
                status_code=status.HTTP_200_OK,
                status="success",
                message="Group deleted successfully",
            )
        except Exception as e:
            await db.rollback()
            if isinstance(e, (NotFoundException, ForbiddenException)):
                raise e
            raise InternalServerErrorException(message=str(e)) from e

    # ==================== MEMBERSHIP MANAGEMENT ====================

    async def add_member(
        self,
        *,
        db: AsyncSession,
        group_id: str,
        user_id: str,
        added_by: str,
        role: str = "member",
    ) -> dict[str, Any]:
        """Add a member to a group."""
        try:
            # Check if adder is owner or admin
            adder_member = await self.member_repo.get_member(db, group_id, added_by)
            if not adder_member or adder_member.role not in ["owner", "admin"]:
                raise ForbiddenException(
                    message="Only group owners and admins can add members"
                )

            # Check if user is already a member
            existing_member = await self.member_repo.get_member(db, group_id, user_id)
            if existing_member and existing_member.is_active:
                raise ConflictException(message="User is already a member of the group")

            # Check if user exists
            user = await User.get_by_id(user_id, db)
            if not user:
                raise NotFoundException(message="User not found")

            # Add the member
            member = await self.member_repo.add_member(
                db=db,
                group_id=group_id,
                user_id=user_id,
                role=role,
                invited_by=added_by,
            )
            if not member:
                raise ConflictException(message="Failed to add member")

            await db.commit()

            return response_builder(
                status_code=status.HTTP_201_CREATED,
                status="success",
                message="Member added successfully",
                data={
                    "member": member.to_dict(),
                    "user": user.to_dict(),
                },
            )
        except Exception as e:
            await db.rollback()
            if isinstance(
                e, (NotFoundException, ForbiddenException, ConflictException)
            ):
                raise e
            raise InternalServerErrorException(message=str(e)) from e

    async def remove_member(
        self,
        *,
        db: AsyncSession,
        group_id: str,
        user_id: str,
        removed_by: str,
    ) -> dict[str, Any]:
        """Remove a member from a group."""
        try:
            # Check if remover is owner or admin
            remover_member = await self.member_repo.get_member(db, group_id, removed_by)
            if not remover_member or remover_member.role not in ["owner", "admin"]:
                raise ForbiddenException(
                    message="Only group owners and admins can remove members"
                )

            # Prevent removing the last owner
            if user_id == removed_by:
                # Check if there are other owners/admins
                members = await self.member_repo.get_group_members(db, group_id)
                owner_count = sum(
                    1
                    for m in members
                    if m.role == "owner" and m.is_active and m.user_id != user_id
                )
                if owner_count == 0:
                    raise ConflictException(
                        message="Cannot remove the last owner. Transfer ownership first."
                    )

            # Remove the member
            success = await self.member_repo.remove_member(db, group_id, user_id)
            if not success:
                raise NotFoundException(message="Member not found or already removed")

            await db.commit()

            return response_builder(
                status_code=status.HTTP_200_OK,
                status="success",
                message="Member removed successfully",
            )
        except Exception as e:
            await db.rollback()
            if isinstance(
                e, (NotFoundException, ForbiddenException, ConflictException)
            ):
                raise e
            raise InternalServerErrorException(message=str(e)) from e

    async def get_group_members(
        self, db: AsyncSession, group_id: str, user_id: str | None = None
    ) -> dict[str, Any]:
        """Get members of a group."""
        try:
            # Check if user is a member (if user_id provided)
            if user_id:
                is_member = (
                    await self.member_repo.get_member(db, group_id, user_id) is not None
                )
                if not is_member:
                    raise ForbiddenException(
                        message="You are not a member of this group"
                    )

            # Get members
            members = await self.member_repo.get_group_members(db, group_id)

            # Get user details for each member
            member_data = []
            for member in members:
                if member.is_active:
                    user = await User.get_by_id(str(member.user_id), db)
                    if user:
                        member_data.append(
                            {
                                "member": member.to_dict(),
                                "user": ChatSerializers._serialize_user(user),
                            }
                        )

            return response_builder(
                status_code=status.HTTP_200_OK,
                status="success",
                message="Group members retrieved",
                data={
                    "members": member_data,
                    "total_count": len(member_data),
                    "owner_count": sum(
                        1 for m in members if m.role == "owner" and m.is_active
                    ),
                    "admin_count": sum(
                        1 for m in members if m.role == "admin" and m.is_active
                    ),
                },
            )
        except Exception as e:
            if isinstance(e, ForbiddenException):
                raise e
            raise InternalServerErrorException(message=str(e)) from e

    async def transfer_ownership(
        self,
        *,
        db: AsyncSession,
        group_id: str,
        current_owner_id: str,
        new_owner_id: str,
    ) -> dict[str, Any]:
        """Transfer group ownership to another member."""
        try:
            # Verify current owner
            current_member = await self.member_repo.get_member(
                db, group_id, current_owner_id
            )
            if not current_member or current_member.role != "owner":
                raise ForbiddenException(message="You are not the group owner")

            # Verify new owner is a member
            new_member = await self.member_repo.get_member(db, group_id, new_owner_id)
            if not new_member or not new_member.is_active:
                raise NotFoundException(
                    message="New owner is not a member of the group"
                )

            # Transfer ownership
            success = await self.member_repo.transfer_ownership(
                db=db,
                group_id=group_id,
                new_owner_id=new_owner_id,
                current_owner_id=current_owner_id,
            )
            if not success:
                raise InternalServerErrorException(
                    message="Failed to transfer ownership"
                )

            await db.commit()

            return response_builder(
                status_code=status.HTTP_200_OK,
                status="success",
                message="Group ownership transferred successfully",
                data={
                    "group_id": group_id,
                    "previous_owner_id": current_owner_id,
                    "new_owner_id": new_owner_id,
                },
            )
        except Exception as e:
            await db.rollback()
            if isinstance(e, (NotFoundException, ForbiddenException)):
                raise e
            raise InternalServerErrorException(message=str(e)) from e

    # ==================== MESSAGING ====================

    async def send_message(
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
    ) -> dict[str, Any]:
        """Send a message to a group."""
        try:
            # Check if sender is a member of the group
            sender_member = await self.member_repo.get_member(db, group_id, sender_id)
            if not sender_member or not sender_member.is_active:
                raise ForbiddenException(message="You are not a member of this group")

            # Check if group is active
            group = await self.group_repo.get_group_by_id(db, group_id)
            if not group or not group.is_active:
                raise NotFoundException(message="Group not found or is inactive")

            # Validate mentioned users (if any)
            if mentioned_user_ids:
                # Check that all mentioned users are actually members of the group
                for user_id in mentioned_user_ids:
                    mentioned_member = await self.member_repo.get_member(
                        db, group_id, user_id
                    )
                    if not mentioned_member or not mentioned_member.is_active:
                        raise BadRequestException(
                            message=f"User {user_id} is not a member of this group and cannot be mentioned"
                        )

            # Create the message
            message = await self.message_repo.create_message(
                db=db,
                group_id=group_id,
                sender_id=sender_id,
                body=body,
                media_type=media_type,
                media_urls=media_urls,
                media_names=media_names,
                reply_to_message_id=reply_to_message_id,
                mentioned_user_ids=mentioned_user_ids,
            )

            await db.commit()

            # Get sender info for response
            sender = await User.get_by_id(sender_id, db)

            return response_builder(
                status_code=status.HTTP_201_CREATED,
                status="success",
                message="Message sent successfully",
                data={
                    "message": message.to_dict(),
                    "sender": (
                        ChatSerializers._serialize_user(sender) if sender else None
                    ),
                },
            )
        except Exception as e:
            await db.rollback()
            if isinstance(
                e, (NotFoundException, ForbiddenException, BadRequestException)
            ):
                raise e
            raise InternalServerErrorException(message=str(e)) from e

    async def get_group_messages(
        self,
        *,
        db: AsyncSession,
        group_id: str,
        user_id: str,
        page: int = 1,
        page_size: int = 50,
        before_message_id: str | None = None,
    ) -> dict[str, Any]:
        """Get messages for a group."""
        try:
            # Check if user is a member
            is_member = (
                await self.member_repo.get_member(db, group_id, user_id) is not None
            )
            if not is_member:
                raise ForbiddenException(message="You are not a member of this group")

            # Get messages
            messages, total_count = await self.message_repo.get_group_messages(
                db=db,
                group_id=group_id,
                page=page,
                page_size=page_size,
                before_message_id=before_message_id,
            )

            # Get sender details for each message
            message_data = []
            for message in messages:
                sender = await User.get_by_id(str(message.sender_id), db)
                message_data.append(
                    {
                        "message": message.to_dict(),
                        "sender": (
                            ChatSerializers._serialize_user(sender) if sender else None
                        ),
                    }
                )

            return response_builder(
                status_code=status.HTTP_200_OK,
                status="success",
                message="Group messages retrieved",
                data={
                    "messages": message_data,
                    "pagination": {
                        "page": page,
                        "page_size": page_size,
                        "total_count": total_count,
                        "total_pages": (total_count + page_size - 1) // page_size,
                        "has_next": (page * page_size) < total_count,
                        "has_prev": page > 1,
                    },
                },
            )
        except Exception as e:
            if isinstance(e, ForbiddenException):
                raise e
            raise InternalServerErrorException(message=str(e)) from e

    async def update_message(
        self,
        *,
        db: AsyncSession,
        group_id: str,
        message_id: str,
        user_id: str,
        body: str | None = None,
        media_type: str | None = None,
        media_urls: list[str] | None = None,
        media_names: list[str] | None = None,
    ) -> dict[str, Any]:
        """Update a group message."""
        try:
            # Get the message
            message = await self.message_repo.get_message_by_id(db, message_id)
            if not message:
                raise NotFoundException(message="Message not found")
            if str(message.group_id) != str(group_id):
                raise NotFoundException(message="Message not found")

            # Check if user is the sender
            if str(message.sender_id) != user_id:
                raise ForbiddenException(message="You can only edit your own messages")

            # Update the message
            updated_message = await self.message_repo.update_message(
                db=db,
                message_id=message_id,
                body=body,
                media_type=media_type,
                media_urls=media_urls,
                media_names=media_names,
            )
            if not updated_message:
                raise NotFoundException(message="Message not found")

            await db.commit()

            # Get sender info
            sender = await User.get_by_id(str(updated_message.sender_id), db)

            return response_builder(
                status_code=status.HTTP_200_OK,
                status="success",
                message="Message updated successfully",
                data={
                    "message": updated_message.to_dict(),
                    "sender": sender.to_dict() if sender else None,
                },
            )
        except Exception as e:
            await db.rollback()
            if isinstance(e, (NotFoundException, ForbiddenException)):
                raise e
            raise InternalServerErrorException(message=str(e)) from e

    async def delete_message(
        self, db: AsyncSession, group_id: str, message_id: str, user_id: str
    ) -> dict[str, Any]:
        """Delete a group message."""
        try:
            # Get the message
            message = await self.message_repo.get_message_by_id(db, message_id)
            if not message:
                raise NotFoundException(message="Message not found")
            if str(message.group_id) != str(group_id):
                raise NotFoundException(message="Message not found")

            # Check if user is the sender
            if str(message.sender_id) != user_id:
                raise ForbiddenException(
                    message="You can only delete your own messages"
                )

            # Delete the message
            success = await self.message_repo.delete_message(db, message_id)
            if not success:
                raise NotFoundException(message="Message not found")

            await db.commit()

            return response_builder(
                status_code=status.HTTP_200_OK,
                status="success",
                message="Message deleted successfully",
            )
        except Exception as e:
            await db.rollback()
            if isinstance(e, (NotFoundException, ForbiddenException)):
                raise e
            raise InternalServerErrorException(message=str(e)) from e

    async def get_mentioned_messages(
        self, db: AsyncSession, user_id: str, limit: int = 50
    ) -> dict[str, Any]:
        """Get messages where a user was mentioned."""
        try:
            # Check if user exists
            user = await User.get_by_id(user_id, db)
            if not user:
                raise NotFoundException(message="User not found")

            # Get mentioned messages
            messages = await self.message_repo.get_mentioned_messages(
                db=db, user_id=user_id, limit=limit
            )

            # Get sender details for each message
            message_data = []
            for message in messages:
                sender = await User.get_by_id(str(message.sender_id), db)
                message_data.append(
                    {
                        "message": message.to_dict(),
                        "sender": sender.to_dict() if sender else None,
                    }
                )

            return response_builder(
                status_code=status.HTTP_200_OK,
                status="success",
                message="Mentioned messages retrieved",
                data={"messages": message_data, "count": len(message_data)},
            )
        except Exception as e:
            if isinstance(e, NotFoundException):
                raise e
            raise InternalServerErrorException(message=str(e)) from e


group_service = GroupService()
