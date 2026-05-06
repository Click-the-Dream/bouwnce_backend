from pydantic import BaseModel, Field
from typing import Annotated
import uuid

class SendMessagePayload(BaseModel):
    recipient_id: Annotated[uuid.UUID, Field(..., description="Recipient user id (uuid)")]
    body: Annotated[str, Field(..., min_length=1, max_length=4000)]

