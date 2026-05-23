from typing import Any

from fastapi import HTTPException, status


class ApiException(HTTPException):
    def __init__(self, *, status_code: int, message: str, data: Any | None = None):
        detail = {"status_code": status_code, "status": "error", "message": message}
        if data:
            detail["data"] = data

        super().__init__(status_code, detail)


class BadRequestException(ApiException):
    def __init__(self, message: str, data: Any | None = None):

        super().__init__(
            status_code=status.HTTP_400_BAD_REQUEST, message=message, data=data
        )


class UnAuthorizedException(ApiException):
    def __init__(self, message: str, data: Any | None = None):
        super().__init__(
            status_code=status.HTTP_401_UNAUTHORIZED, message=message, data=data
        )


class ForbiddenException(ApiException):
    def __init__(self, message: str, data: Any | None = None):
        super().__init__(
            status_code=status.HTTP_403_FORBIDDEN, message=message, data=data
        )


class NotFoundException(ApiException):
    def __init__(self, message: str, data: Any | None = None):
        super().__init__(
            status_code=status.HTTP_404_NOT_FOUND, message=message, data=data
        )


class ConflictException(ApiException):
    def __init__(self, message: str, data: Any | None = None):
        super().__init__(
            status_code=status.HTTP_409_CONFLICT, message=message, data=data
        )


class GoneException(ApiException):
    def __init__(self, message: str, data: Any | None = None):
        super().__init__(status_code=status.HTTP_410_GONE, message=message, data=data)


class InternalServerErrorException(ApiException):
    def __init__(self, message: str, data: Any | None = None):

        super().__init__(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            message=message,
            data=data,
        )
