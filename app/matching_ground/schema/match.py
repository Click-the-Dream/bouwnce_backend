from pydantic import BaseModel, Field
from typing import Annotated


class RespondMatchRequestPayload(BaseModel):
    accepted: Annotated[bool, Field(..., description="Accept or decline request", examples=[True])]
    
class CreateMatchRequestPayload(BaseModel):
    target_user_id: Annotated[str, Field(...)]
    note: Annotated[str | None, Field(default=None, max_length=1000)]
