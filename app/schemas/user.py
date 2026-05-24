from enum import Enum
from typing import Annotated

from pydantic import BaseModel, EmailStr, Field

from app.utils.responses import BaseResponse


class RoleEnum(Enum):
    USER = "user"
    VENDOR = "vendor"
    ADMIN = "admin"


class Image(BaseModel):
    url: Annotated[str, Field(examples=["http://image_url.png"])]


class UserBase(BaseModel):
    full_name: Annotated[str, Field(min_length=2, examples=["John Doe"])]
    email: Annotated[EmailStr, Field(examples=["johndoe@example.com"])]
    username: Annotated[str, Field(min_length=2, examples=["johndoe"])]
    bio: Annotated[str | None, Field(min_length=2, examples=["Hello I'm John!"])] = None
    date_of_birth: Annotated[str | None, Field(...)] = None
    role: Annotated[RoleEnum, Field(description="Role of user")]
    is_store_owner: Annotated[bool, Field(examples=[False])] = False


class UserCreate(UserBase):
    pass


class UserResponsSchema(UserBase):
    id: Annotated[str, Field(examples=["52fecfe4-c101-4d24-9f82-8d66f145dd1d"])]
    profile_pic: Annotated[Image | None, Field(...)]
    profile_banner: Annotated[Image | None, Field(...)]
    is_active: Annotated[bool, Field(examples=[True])]
    otp: Annotated[str | None, Field(examples=["123456"])] = None
    created_at: Annotated[str, Field(examples=["2025-04-03"])]
    updated_at: Annotated[str, Field(examples=["2025-04-03"])]


class UserResponse(BaseResponse):
    data: Annotated[UserResponsSchema, Field(description="User response data")]


class LoginUserResponseSchema(BaseModel):
    user: Annotated[UserResponsSchema, Field(description="User Response data")]
    access_token: Annotated[str, Field(description="Access token to login")]


class LoginUserResponse(BaseResponse):
    data: Annotated[
        LoginUserResponseSchema, Field(description="Login user response data")
    ]


class PaginatedUserResponseSchema(BaseModel):
    users: Annotated[
        list[UserResponsSchema], Field(description="List of User response")
    ]
    page: Annotated[int, Field(examples=[2])]
    page_size: Annotated[int, Field(examples=[10])]
    total: Annotated[int, Field(examples=[100])]


class PaginatedUserResponse(BaseResponse):
    data: Annotated[
        PaginatedUserResponseSchema, Field(description="Paginated user response")
    ]


class CodeVerification(BaseModel):
    email: Annotated[EmailStr, Field(examples=["johndoe@example.com"])]
    code: Annotated[str, Field(min_length=6, max_length=6, examples=["123456"])]


class LoginUser(BaseModel):
    email: Annotated[EmailStr, Field(examples=["johndoe@example.com"])]


class UpdateUser(BaseModel):
    full_name: Annotated[str | None, Field(min_length=2, examples=["John Doe"])] = None
    email: Annotated[EmailStr | None, Field(examples=["johndoe@example.com"])] = None
    username: Annotated[str | None, Field(min_length=2, examples=["johnDoe"])] = None
    bio: Annotated[str | None, Field(min_length=2, examples=["Hello I'm John!"])] = None
    role: Annotated[RoleEnum | None, Field(description="Role of user")] = None
