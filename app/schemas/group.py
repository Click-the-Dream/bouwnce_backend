"""
Group Chat Schemas
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field


class GroupBase(BaseModel):
    """Base group schema."""

    name: Annotated[
        str,
        Field(..., min_length=1, max_length=100, description="Group name"),
    ]
    description: Annotated[
        str | None,
        Field(None, max_length=500, description="Group description"),
    ]


class GroupCreate(GroupBase):
    """Schema for creating a new group."""

    pass


class GroupUpdate(BaseModel):
    """Schema for updating group details."""

    name: Annotated[
        str | None,
        Field(None, min_length=1, max_length=100, description="Group name"),
    ]
    description: Annotated[
        str | None,
        Field(None, max_length=500, description="Group description"),
    ]


class GroupResponse(GroupBase):
    """Schema for group response."""

    id: Annotated[uuid.UUID, Field(..., description="Group ID")]
    created_by: Annotated[uuid.UUID, Field(..., description="Creator user ID")]
    is_active: Annotated[bool, Field(..., description="Whether group is active")]
    created_at: Annotated[datetime, Field(..., description="Creation timestamp")]
    updated_at: Annotated[datetime, Field(..., description="Last update timestamp")]
    member_count: Annotated[int, Field(..., description="Number of members in group")]
    is_owner: Annotated[bool, Field(..., description="Whether current user is owner")]

    model_config = ConfigDict(from_attributes=True)


class GroupMemberBase(BaseModel):
    """Base group member schema."""

    role: Annotated[
        str,
        Field(
            default="member",
            description="Member role (owner, admin, member, moderator)",
        ),
    ]


class GroupMemberCreate(GroupMemberBase):
    """Schema for adding a member to a group."""

    user_id: Annotated[
        uuid.UUID,
        Field(..., description="User ID to add to the group"),
    ]


class GroupMemberResponse(BaseModel):
    """Schema for group member response."""

    id: Annotated[uuid.UUID, Field(..., description="Member record ID")]
    group_id: Annotated[uuid.UUID, Field(..., description="Group ID")]
    user_id: Annotated[uuid.UUID, Field(..., description="User ID")]
    role: Annotated[str, Field(..., description="Member role")]
    joined_at: Annotated[datetime, Field(..., description="Join timestamp")]
    invited_by: Annotated[uuid.UUID | None, Field(None, description="Inviter user ID")]
    is_active: Annotated[bool, Field(..., description="Whether membership is active")]

    # User details (populated when fetching with user info)
    user: dict | None = None

    model_config = ConfigDict(from_attributes=True)


class GroupMessageBase(BaseModel):
    """Base group message schema."""

    body: Annotated[
        str,
        Field(..., min_length=1, max_length=4000, description="Message content"),
    ]
    media_type: Annotated[
        str | None,
        Field(None, description="Media type: image|video|file|audio"),
    ]
    media_urls: Annotated[
        list[str] | None,
        Field(None, description="List of media URLs"),
    ]
    media_names: Annotated[
        list[str] | None,
        Field(None, description="List of media file names"),
    ]
    reply_to_message_id: Annotated[
        uuid.UUID | None,
        Field(None, description="ID of message being replied to"),
    ]
    mentioned_user_ids: Annotated[
        list[uuid.UUID] | None,
        Field(None, description="List of mentioned user IDs"),
    ]


class GroupMessageCreate(GroupMessageBase):
    """Schema for creating a new group message."""

    pass


class GroupMessageResponse(GroupMessageBase):
    """Schema for group message response."""

    id: Annotated[uuid.UUID, Field(..., description="Message ID")]
    group_id: Annotated[uuid.UUID, Field(..., description="Group ID")]
    sender_id: Annotated[uuid.UUID, Field(..., description="Sender user ID")]
    created_at: Annotated[datetime, Field(..., description="Message timestamp")]
    edited_at: Annotated[
        datetime | None, Field(None, description="Last edit timestamp")
    ]
    deleted_for_everyone_at: datetime | None = None
    is_edited: Annotated[bool, Field(..., description="Whether message was edited")]
    mentioned_user_ids: Annotated[
        list[uuid.UUID] | None, Field(None, description="List of mentioned user IDs")
    ]

    # Sender details (populated when fetching with user info)
    sender: dict | None = None

    model_config = ConfigDict(from_attributes=True)


class GroupMessageUpdate(BaseModel):
    """Schema for updating a group message."""

    body: Annotated[
        str | None,
        Field(None, min_length=1, max_length=4000, description="Message content"),
    ]
    media_type: Annotated[
        str | None,
        Field(None, description="Media type: image|video|file|audio"),
    ]
    media_urls: Annotated[
        list[str] | None,
        Field(None, description="List of media URLs"),
    ]
    media_names: Annotated[
        list[str] | None,
        Field(None, description="List of media file names"),
    ]


class GroupMessageDelete(BaseModel):
    """Deletion scope for a group message."""

    message_id: Annotated[uuid.UUID, Field(..., description="Message to delete")]
    delete_for: Literal["me", "everyone"] = "everyone"


class GroupInviteResponse(BaseModel):
    """Schema for group invite link response."""

    group_id: Annotated[uuid.UUID, Field(..., description="Group ID")]
    group_name: Annotated[str, Field(..., description="Group name")]
    invite_url: Annotated[str, Field(..., description="Group invite URL")]
    expires_at: Annotated[
        datetime, Field(..., description="Invite link expiration timestamp")
    ]
    is_valid: Annotated[bool, Field(..., description="Whether invite link is valid")]


class GroupStatsResponse(BaseModel):
    """Schema for group statistics response."""

    group_id: Annotated[uuid.UUID, Field(..., description="Group ID")]
    group_name: Annotated[str, Field(..., description="Group name")]
    member_count: Annotated[int, Field(..., description="Total number of members")]
    active_member_count: Annotated[
        int, Field(..., description="Number of active members")
    ]
    message_count: Annotated[int, Field(..., description="Total number of messages")]
    owner_count: Annotated[int, Field(..., description="Number of owners")]
    admin_count: Annotated[int, Field(..., description="Number of admins")]
    created_at: Annotated[datetime, Field(..., description="Group creation timestamp")]
    updated_at: Annotated[datetime, Field(..., description="Last update timestamp")]
