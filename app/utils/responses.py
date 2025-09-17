from typing import Any

from fastapi.encoders import jsonable_encoder
from fastapi.responses import JSONResponse


def response_builder(
    status_code: int,
    message: str,
    data: dict[str, Any] | list[Any] | None = None,
    status: str = "success",
) -> dict[str, Any]:

    response_data = {"status": status, "status_code": status_code, "message": message}

    if data is not None:
        response_data["data"] = data

    return JSONResponse(
        status_code=status_code, content=jsonable_encoder(response_data)
    )
