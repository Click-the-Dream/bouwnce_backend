"""
Group Chat API Endpoints
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, HTTPException, Query, status

from app.api.dependencies import (
    CurrentActiveUser,
    dbSessionDep,
)
from app.schemas.group import (
    GroupCreate,
    GroupInviteResponse,
    GroupMemberCreate,
    GroupMemberResponse,
    GroupMessageCreate,
    GroupMessageResponse,
    GroupMessageUpdate,
    GroupResponse,
    GroupStatsResponse,
    GroupUpdate,
)
from app.service.group_service import group_service

# Create router
router = APIRouter(prefix="/groups", tags=["Groups"])


@router.post(
    "",
    response_model=GroupResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new group",
)
async def create_group(
    group_data: GroupCreate,
    current_user: CurrentActiveUser,
    db: dbSessionDep,
) -> GroupResponse:
    """Create a new group.

    - **name**: Group name (required, 1-100 characters)
    - **description**: Optional group description (max 500 characters)
    """
    result = await group_service.create_group(
        db=db,
        name=group_data.name,
        created_by=str(current_user.id),
        description=group_data.description,
    )
    return GroupResponse(**result["data"]["group"])


@router.get(
    "",
    response_model=list[GroupResponse],
    summary="Get user's groups",
)
async def get_user_groups(
    current_user: CurrentActiveUser,
    db: dbSessionDep,
    include_inactive: Annotated[
        bool, Query(description="Include inactive groups")
    ] = False,
) -> list[GroupResponse]:
    """Get all groups for the current user."""
    result = await group_service.get_user_groups(
        db=db,
        user_id=str(current_user.id),
        include_inactive=include_inactive,
    )
    return [
        GroupResponse(**group_data["group"]) for group_data in result["data"]["groups"]
    ]


@router.get(
    "/{group_id}",
    response_model=GroupResponse,
    summary="Get group details",
)
async def get_group(
    group_id: uuid.UUID,
    current_user: CurrentActiveUser,
    db: dbSessionDep,
) -> GroupResponse:
    """Get details of a specific group."""
    result = await group_service.get_group_by_id(
        db=db,
        group_id=str(group_id),
        user_id=str(current_user.id),
    )
    return GroupResponse(**result["data"]["group"])


@router.patch(
    "/{group_id}",
    response_model=GroupResponse,
    summary="Update group details",
)
async def update_group(
    group_id: uuid.UUID,
    group_data: GroupUpdate,
    current_user: CurrentActiveUser,
    db: dbSessionDep,
) -> GroupResponse:
    """Update group details.

    - **name**: New group name (optional, 1-100 characters)
    - **description**: New group description (optional, max 500 characters)
    """
    result = await group_service.update_group(
        db=db,
        group_id=str(group_id),
        user_id=str(current_user.id),
        name=group_data.name,
        description=group_data.description,
    )
    return GroupResponse(**result["data"]["group"])


@router.delete(
    "/{group_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a group",
)
async def delete_group(
    group_id: uuid.UUID,
    current_user: CurrentActiveUser,
    db: dbSessionDep,
) -> None:
    """Delete a group (soft delete)."""
    await group_service.delete_group(
        db=db,
        group_id=str(group_id),
        user_id=str(current_user.id),
    )
    return None


# ==================== MEMBERSHIP MANAGEMENT ENDPOINTS ====================


@router.post(
    "/{group_id}/members",
    response_model=GroupMemberResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Add a member to the group",
)
async def add_member(
    group_id: uuid.UUID,
    member_data: GroupMemberCreate,
    current_user: CurrentActiveUser,
    db: dbSessionDep,
) -> GroupMemberResponse:
    """Add a member to the group.

    - **user_id**: ID of user to add to the group
    - **role**: Member role (owner, admin, member, moderator) - defaults to "member"
    """
    result = await group_service.add_member(
        db=db,
        group_id=str(group_id),
        user_id=str(member_data.user_id),
        added_by=str(current_user.id),
        role=member_data.role,
    )
    return GroupMemberResponse(**result["data"]["member"])


@router.delete(
    "/{group_id}/members/{user_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Remove a member from the group",
)
async def remove_member(
    group_id: uuid.UUID,
    user_id: uuid.UUID,
    current_user: CurrentActiveUser,
    db: dbSessionDep,
) -> None:
    """Remove a member from the group."""
    await group_service.remove_member(
        db=db,
        group_id=str(group_id),
        user_id=str(user_id),
        removed_by=str(current_user.id),
    )
    return None


@router.get(
    "/{group_id}/members",
    response_model=list[GroupMemberResponse],
    summary="Get group members",
)
async def get_group_members(
    group_id: uuid.UUID,
    current_user: CurrentActiveUser,
    db: dbSessionDep,
) -> list[GroupMemberResponse]:
    """Get all members of a group."""
    result = await group_service.get_group_members(
        db=db,
        group_id=str(group_id),
        user_id=str(current_user.id),
    )
    return [
        GroupMemberResponse(
            **member_data["member"],
            user=member_data["user"],
        )
        for member_data in result["data"]["members"]
    ]


@router.post(
    "/{group_id}/transfer-ownership",
    response_model=dict,
    summary="Transfer group ownership",
)
async def transfer_ownership(
    group_id: uuid.UUID,
    new_owner_id: uuid.UUID,
    current_user: CurrentActiveUser,
    db: dbSessionDep,
) -> dict:
    """Transfer group ownership to another member.

    - **new_owner_id**: ID of the user to transfer ownership to
    """
    result = await group_service.transfer_ownership(
        db=db,
        group_id=str(group_id),
        current_owner_id=str(current_user.id),
        new_owner_id=str(new_owner_id),
    )
    return result["data"]


# ==================== MESSAGING ENDPOINTS ====================


@router.post(
    "/{group_id}/messages",
    response_model=GroupMessageResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Send a message to the group",
)
async def send_message(
    group_id: uuid.UUID,
    message_data: GroupMessageCreate,
    current_user: CurrentActiveUser,
    db: dbSessionDep,
) -> GroupMessageResponse:
    """Send a message to the group.

    - **body**: Message content (required, 1-4000 characters)
    - **media_type**: Media type (image|video|file|audio, optional)
    - **media_urls**: List of media URLs (optional)
    - **media_names**: List of media file names (optional)
    - **reply_to_message_id**: ID of message being replied to (optional)
    - **mentioned_user_ids**: List of mentioned user IDs (optional)
    """
    result = await group_service.send_message(
        db=db,
        group_id=str(group_id),
        sender_id=str(current_user.id),
        body=message_data.body,
        media_type=message_data.media_type,
        media_urls=message_data.media_urls,
        media_names=message_data.media_names,
        reply_to_message_id=message_data.reply_to_message_id,
        mentioned_user_ids=message_data.mentioned_user_ids,
    )
    return GroupMessageResponse(
        **result["data"]["message"],
        sender=result["data"]["sender"],
    )


@router.get(
    "/{group_id}/messages",
    response_model=list[GroupMessageResponse],
    summary="Get group messages",
)
async def get_group_messages(
    group_id: uuid.UUID,
    current_user: CurrentActiveUser,
    db: dbSessionDep,
    page: Annotated[int, Query(ge=1, description="Page number (starts at 1)")] = 1,
    page_size: Annotated[
        int, Query(ge=1, le=100, description="Number of messages per page")
    ] = 50,
    before_message_id: Annotated[
        uuid.UUID | None, Query(description="Get messages before this message ID")
    ] = None,
) -> list[GroupMessageResponse]:
    """Get messages for a group with pagination.

    - **page**: Page number (starts at 1)
    - **page_size**: Number of messages per page (1-100)
    - **before_message_id**: Get messages before this message ID (for pagination)
    """
    result = await group_service.get_group_messages(
        db=db,
        group_id=str(group_id),
        user_id=str(current_user.id),
        page=page,
        page_size=page_size,
        before_message_id=str(before_message_id) if before_message_id else None,
    )
    return [
        GroupMessageResponse(
            **message_data["message"],
            sender=message_data["sender"],
        )
        for message_data in result["data"]["messages"]
    ]


@router.patch(
    "/{group_id}/messages/{message_id}",
    response_model=GroupMessageResponse,
    summary="Update a group message",
)
async def update_message(
    group_id: uuid.UUID,
    message_id: uuid.UUID,
    message_data: GroupMessageUpdate,
    current_user: CurrentActiveUser,
    db: dbSessionDep,
) -> GroupMessageResponse:
    """Update a group message.

    - **body**: New message content (optional, 1-4000 characters)
    - **media_type**: New media type (optional)
    - **media_urls**: New list of media URLs (optional)
    - **media_names**: New list of media file names (optional)
    """
    result = await group_service.update_message(
        db=db,
        group_id=str(group_id),
        message_id=str(message_id),
        user_id=str(current_user.id),
        body=message_data.body,
        media_type=message_data.media_type,
        media_urls=message_data.media_urls,
        media_names=message_data.media_names,
    )
    return GroupMessageResponse(**result["data"]["message"])


@router.delete(
    "/{group_id}/messages/{message_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a group message",
)
async def delete_message(
    group_id: uuid.UUID,
    message_id: uuid.UUID,
    current_user: CurrentActiveUser,
    db: dbSessionDep,
) -> None:
    """Delete a group message."""
    await group_service.delete_message(
        db=db,
        group_id=str(group_id),
        message_id=str(message_id),
        user_id=str(current_user.id),
    )
    return None


@router.get(
    "/{group_id}/mentioned",
    response_model=list[GroupMessageResponse],
    summary="Get messages where user was mentioned",
)
async def get_mentioned_messages(
    group_id: uuid.UUID,
    current_user: CurrentActiveUser,
    db: dbSessionDep,
    limit: Annotated[
        int, Query(ge=1, le=100, description="Number of messages to return")
    ] = 50,
) -> list[GroupMessageResponse]:
    """Get messages where the current user was mentioned."""
    result = await group_service.get_mentioned_messages(
        db=db,
        user_id=str(current_user.id),
        limit=limit,
    )
    return [
        GroupMessageResponse(**message_data["message"])
        for message_data in result["data"]["messages"]
    ]


# ==================== GROUP INVITE ENDPOINTS ====================


@router.post(
    "/{group_id}/invite",
    response_model=GroupInviteResponse,
    summary="Generate group invite link",
)
async def create_invite_link(
    group_id: uuid.UUID,
    current_user: CurrentActiveUser,
    db: dbSessionDep,
) -> GroupInviteResponse:
    """Generate an invite link for the group.

    Only group owners and admins can generate invite links.
    """
    # Check if user is owner or admin
    member = await group_service.member_repo.get_member(
        db, str(group_id), str(current_user.id)
    )
    if not member or member.role not in ["owner", "admin"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only group owners and admins can generate invite links",
        )

    # Get group details for the response
    group_result = await group_service.get_group_by_id(
        db=db, group_id=str(group_id), user_id=str(current_user.id)
    )
    group_data = group_result["data"]["group"]

    # TODO: In a real implementation, you would:
    # 1. Generate a secure, unique token
    # 2. Store it in database with expiration
    # 3. Return the actual URL that points to your frontend
    # For now, we'll create a placeholder that follows the expected format
    import secrets
    from datetime import datetime, timedelta

    # Generate a secure token (in production, store this in DB)
    invite_token = secrets.token_urlsafe(32)
    expire_time = datetime.now() + timedelta(hours=24)  # 24 hour expiry

    # Construct the invite URL (this would point to your frontend)
    invite_url = f"/groups/{group_id}/join?token={invite_token}"

    return GroupInviteResponse(
        group_id=group_id,
        group_name=group_data["name"],
        invite_url=invite_url,
        expires_at=expire_time,
        is_valid=True,
    )


# ==================== GROUP STATISTICS ENDPOINT ====================


@router.get(
    "/{group_id}/stats",
    response_model=GroupStatsResponse,
    summary="Get group statistics",
)
async def get_group_stats(
    group_id: uuid.UUID,
    current_user: CurrentActiveUser,
    db: dbSessionDep,
) -> GroupStatsResponse:
    """Get statistics for a group."""
    # Check if user is a member
    is_member = await group_service.member_repo.get_member(
        db, str(group_id), str(current_user.id)
    )
    if not is_member:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You must be a member of the group to view statistics",
        )

    # Get actual statistics
    group_result = await group_service.get_group_by_id(
        db=db, group_id=str(group_id), user_id=str(current_user.id)
    )
    group_data = group_result["data"]["group"]

    members_result = await group_service.get_group_members(
        db=db, group_id=str(group_id), user_id=str(current_user.id)
    )
    members = members_result["data"]["members"]

    # Get actual message count
    message_result = await group_service.message_repo.get_group_messages(
        db=db,
        group_id=str(group_id),
        page=1,
        page_size=1,  # Just to get count
    )
    message_count = message_result[1]  # total_count from the tuple

    return GroupStatsResponse(
        group_id=group_id,
        group_name=group_data["name"],
        member_count=len(members),
        active_member_count=len([m for m in members if m["member"]["is_active"]]),
        message_count=message_count,
        owner_count=len(
            [
                m
                for m in members
                if m["member"]["role"] == "owner" and m["member"]["is_active"]
            ]
        ),
        admin_count=len(
            [
                m
                for m in members
                if m["member"]["role"] == "admin" and m["member"]["is_active"]
            ]
        ),
        created_at=datetime.fromisoformat(group_data["created_at"]),
        updated_at=datetime.fromisoformat(group_data["updated_at"]),
    )
