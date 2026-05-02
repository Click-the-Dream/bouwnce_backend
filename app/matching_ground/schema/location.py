from pydantic import BaseModel, Field
from typing import Annotated
import uuid

class LocationUpsertRequest(BaseModel):
    lat: Annotated[float, Field(..., examples=[6.5244])]
    lon: Annotated[float, Field(..., examples=[3.3792])]


class LocationResponse(BaseModel):
    id: Annotated[uuid.UUID, Field(..., examples={'12123-32543-23454-esfere-3545'})]
    user_id: Annotated[uuid.UUID, Field(..., examples={'12123-32543-23454-esfere-3545'})]
    lat: Annotated[float, Field(..., examples=[6.5244])]
    lon: Annotated[float, Field(..., examples=[3.3792])]