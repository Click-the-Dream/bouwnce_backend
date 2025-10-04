from pydantic import BaseModel, Field
from typing import Annotated, Optional

class StoreCreate(BaseModel):
    name: Annotated[str, Field(min_length=2, examples=["My Awesome Store"])]
    
class StoreResponse(BaseModel):
    id: Annotated[str, Field(examples=["52fecfe4-c101-4d24-9f82-8d66f145dd1d"])]
    user_id: Annotated[str, Field(examples=["52fecfe4-c101-4d24-9f82-8d66f145dd1d"])]
    name: Annotated[str, Field(min_length=2, examples=["My Awesome Store"])]
    created_at: Annotated[str, Field(examples=["2025-04-03"])]
    updated_at: Annotated[str, Field(examples=["2025-04-03"])]
    
class StoreUpdate(BaseModel):
    name: Annotated[Optional[str], Field(min_length=2, examples=["My Even More Awesome Store"])] = None

class StoreDelete(BaseModel):
    id: Annotated[str, Field(examples=["52fecfe4-c101-4d24-9f82-8d66f145dd1d"])]