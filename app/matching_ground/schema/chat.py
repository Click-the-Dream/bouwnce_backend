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
