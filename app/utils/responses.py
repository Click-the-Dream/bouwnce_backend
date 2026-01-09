from typing import Annotated, Any, Literal

from pydantic import BaseModel, Field


class BaseResponse(BaseModel):
    status_code: Annotated[int, Field(examples=[200])]
    status: Annotated[Literal["success", "error"], Field(examples=["success", "error"])]
    message: Annotated[str, Field(examples=["message is successful"])]
    data: dict[str, Any] | list[Any] | None


# 400
class BadRequestResponse(BaseModel):
    status_code: int = Field(default=400, examples=[400])
    status: Literal["error"] = Field(default="error", examples=["error"])
    message: str = Field(default="Bad Request", examples=["Bad Request"])


# 401
class UnauthorizedResponse(BaseModel):
    status_code: int = Field(default=401, examples=[401])
    status: Literal["error"] = Field(default="error", examples=["error"])
    message: str = Field(default="Unauthorized", examples=["Unauthorized"])


# 403
class ForbiddenResponse(BaseModel):
    status_code: int = Field(default=403, examples=[403])
    status: Literal["error"] = Field(default="error", examples=["error"])
    message: str = Field(default="Forbidden", examples=["Forbidden"])


# 404
class NotFoundResponse(BaseModel):
    status_code: int = Field(default=404, examples=[404])
    status: Literal["error"] = Field(default="error", examples=["error"])
    message: str = Field(default="Not Found", examples=["Not Found"])


# 500
class InternalServerErrorResponse(BaseModel):
    status_code: int = Field(default=500, examples=[500])
    status: Literal["error"] = Field(default="error", examples=["error"])
    message: str = Field(
        default="Internal Server Error", examples=["Internal Server Error"]
    )


def response_builder(
    status_code: int,
    message: str,
    data: dict[str, Any] | list[Any] | None = None,
    status: str = "success",
) -> dict[str, Any]:

    response_data = {"status": status, "status_code": status_code, "message": message}

    if data is not None:
        response_data["data"] = data

    # return JSONResponse(
    #     status_code=status_code, content=jsonable_encoder(response_data)
    # )

    return response_data
