import uuid
from typing import Annotated

from pydantic import BaseModel, Field

class SendMessagePayload(BaseModel):
    recipient_id: Annotated[uuid.UUID, Field(..., description="Recipient user id (uuid)")]
    body: Annotated[str, Field(..., min_length=1, max_length=4000)]
    client_id: Annotated[
        str | None, Field(None, max_length=64, description="Client message id", validation_alias="clientId")
    ]
    reply_to_message_id: Annotated[
        uuid.UUID | None,
        Field(
            None,
            description="Reply to message id (uuid)",
            validation_alias="replyToMessageId",
        ),
    ]

    model_config = {"populate_by_name": True}


class MarkConversationReadPayload(BaseModel):
    conversation_id: Annotated[
        uuid.UUID, Field(..., description="Conversation id (uuid)")
    ]
    message_id: Annotated[uuid.UUID, Field(..., description="Message id (uuid)")]


class TypingPayload(BaseModel):
    user_id: Annotated[
        uuid.UUID,
        Field(
            ...,
            description="Other user id (uuid)",
            validation_alias="userId",
        ),
    ]
    is_typing: Annotated[
        bool,
        Field(
            ...,
            description="Whether the user is typing",
            validation_alias="isTyping",
        ),
    ]

    model_config = {"populate_by_name": True}


class UploadImagePayload(BaseModel):
    recipient_id: Annotated[
        uuid.UUID, Field(..., description="Recipient user id (uuid)", validation_alias="recipientId")
    ]
    image_url: Annotated[
        str, Field(..., description="Cloudinary secure URL", validation_alias="imageUrl")
    ]
    caption: Annotated[
        str | None, Field(None, max_length=4000, validation_alias="caption")
    ]
    model_config = {"populate_by_name": True}


class UploadMediaPayload(BaseModel):
    recipient_id: Annotated[
        uuid.UUID,
        Field(..., description="Recipient user id (uuid)", validation_alias="recipientId"),
    ]
    media_url: Annotated[
        str | None,
        Field(None, description="Cloudinary secure URL", validation_alias="mediaUrl"),
    ]
    media_urls: Annotated[
        list[str] | None,
        Field(
            None,
            description="List of Cloudinary secure URLs",
            validation_alias="mediaUrls",
        ),
    ]
    media_type: Annotated[
        str,
        Field(
            ...,
            description="Media type: image|video|file",
            validation_alias="mediaType",
        ),
    ]
    caption: Annotated[str | None, Field(None, max_length=4000)]
    reply_to_message_id: Annotated[
        uuid.UUID | None,
        Field(
            None,
            description="Reply to message id (uuid)",
            validation_alias="replyToMessageId",
        ),
    ]
    model_config = {"populate_by_name": True}
