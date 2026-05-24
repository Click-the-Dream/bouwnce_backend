import uuid
from typing import Annotated

from pydantic import BaseModel, Field


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
    media_urls: Annotated[
        list[str],
        Field(
            ...,
            description="List of Cloudinary secure URLs",
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
