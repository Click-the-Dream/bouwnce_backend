import uuid
from typing import Annotated

from pydantic import BaseModel, Field

class SendMessagePayload(BaseModel):
    recipient_id: Annotated[uuid.UUID, Field(..., description="Recipient user id (uuid)")]
    body: Annotated[str, Field(..., min_length=1, max_length=4000)]


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
