from pydantic import BaseModel, Field
from typing import Annotated

from app.utils.responses import BaseResponse



class InterestResponseSchema(BaseModel):
    category: Annotated[str, Field(description="the interest category name", examples=["sport"])]
    interests: Annotated[list[str], Field(description="List of interest under the category", examples=["running", "joggling", "football"])]

class InterestReponse(BaseResponse):
    data: Annotated[list[InterestResponseSchema], Field(description="List of available interest")]
    
    
class UserInterestCreate(BaseModel):
    interests: Annotated[list[str], Field(description="List of interest to add for user")]
    
class UserInterestResponseSchema(BaseModel):
    interests: Annotated[list[str], Field(description="List of user interest", examples=["running", "joggling", "football"])]
    
    
class UserInterestReponse(BaseResponse):
    data: Annotated[UserInterestResponseSchema, Field(description="List of available interest")]