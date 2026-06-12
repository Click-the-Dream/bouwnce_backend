import uuid
from datetime import datetime
from typing import Annotated

from pydantic import BaseModel, Field


class ChatProfilePic(BaseModel):
    url: str


class ChatUserLite(BaseModel):
    id: uuid.UUID
    username: str | None = None
    full_name: str | None = None
    profile_pic: ChatProfilePic | None = None


class SendMessagePayload(BaseModel):
    recipient_id: Annotated[
        uuid.UUID, Field(..., description="Recipient user id (uuid)")
    ]
    body: Annotated[str, Field(..., min_length=1, max_length=4000)]
    client_id: Annotated[
        str | None, Field(None, max_length=64, description="Client message id")
    ]
    reply_to_message_id: Annotated[
        uuid.UUID | None,
        Field(
            None,
            description="Reply to message id (uuid)",
        ),
    ]


class MarkConversationReadPayload(BaseModel):
    recipient_id: Annotated[uuid.UUID, Field(..., description="Other user id (uuid)")]
    message_id: Annotated[
        uuid.UUID, Field(..., description="Last read message id (uuid)")
    ]
    mark_all: Annotated[
        bool,
        Field(
            False,
            description="If true, mark all unread messages in the conversation as read",
        ),
    ]


class TypingPayload(BaseModel):
    user_id: Annotated[
        uuid.UUID,
        Field(
            ...,
            description="Other user id (uuid)",
        ),
    ]
    is_typing: Annotated[
        bool,
        Field(
            ...,
            description="Whether the user is typing",
        ),
    ]


class UploadMediaPayload(BaseModel):
    recipient_id: Annotated[
        uuid.UUID,
        Field(..., description="Recipient user id (uuid)"),
    ]
    client_id: Annotated[
        str | None,
        Field(None, max_length=64, description="Client message id"),
    ]
    media_urls: Annotated[
        list[str],
        Field(
            ...,
            description="List of Cloudinary secure URLs",
        ),
    ]
    file_name: Annotated[
        str | None,
        Field(
            None, max_length=255, description="Optional file name (for file uploads)"
        ),
    ]
    media_type: Annotated[
        str,
        Field(
            ...,
            description="Media type: image|video|file",
        ),
    ]
    body: Annotated[
        str | None,
        Field(
            None,
            max_length=4000,
            description="Optional text message",
        ),
    ]
    reply_to_message_id: Annotated[
        uuid.UUID | None,
        Field(
            None,
            description="Reply to message id (uuid)",
        ),
    ]


class ChatReadyData(BaseModel):
    user_id: uuid.UUID


class ChatReadyEvent(BaseModel):
    type: str = "chat.ready"
    data: ChatReadyData


class PongEvent(BaseModel):
    type: str = "pong"


class ChatTypingData(BaseModel):
    conversation_id: uuid.UUID
    user: ChatUserLite
    is_typing: bool


class ChatTypingEvent(BaseModel):
    type: str = "chat.typing"
    data: ChatTypingData


class ChatMessageReplyData(BaseModel):
    conversation_id: uuid.UUID
    sender_id: uuid.UUID
    recipient_id: uuid.UUID
    body: str | None = None
    read_at: datetime | None = None
    media_type: str | None = None
    media_urls: list[str] | None = None
    media_name: str | None = None
    reply_to_message_id: uuid.UUID | None = None
    id: uuid.UUID
    created_at: datetime
    updated_at: datetime
    sender: ChatUserLite | None = None
    recipient: ChatUserLite | None = None


class ChatMessageData(ChatMessageReplyData):
    reply_to_message: ChatMessageReplyData | bool = False


class ChatSentData(BaseModel):
    conversation_id: uuid.UUID
    message: ChatMessageData


class ChatSentEvent(BaseModel):
    type: str = "chat.sent"
    client_id: str | None = None
    data: ChatSentData


class ChatSendAckData(BaseModel):
    conversation_id: uuid.UUID
    client_id: str | None = None


class ChatSendAckEvent(BaseModel):
    type: str = "chat.send.ack"
    data: ChatSendAckData


class ChatMessageEvent(BaseModel):
    type: str = "chat.message"
    data: ChatMessageData


class ChatReadUpdatedData(BaseModel):
    conversation_id: uuid.UUID | bool
    message_id: uuid.UUID | None = None
    reader_id: uuid.UUID | None = None
    read: bool
    updated: int
    found: bool | None = None


class ChatReadUpdatedEvent(BaseModel):
    type: str = "chat.read.updated"
    data: ChatReadUpdatedData


class ChatReadAckData(BaseModel):
    conversation_id: uuid.UUID | bool
    reader_id: uuid.UUID | None = None
    read: bool
    updated: int
    found: bool | None = None


class ChatReadAckEvent(BaseModel):
    type: str = "chat.read.ack"
    data: ChatReadAckData
