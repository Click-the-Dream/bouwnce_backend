import traceback
from typing import Any, Mapping
from logger import logger


def log_internal_error(
    *,
    exc: Exception,
    message: str,
    context: Mapping[str, Any] | None = None,
) -> None:

    logger.error(
        message,
        exc_info=exc,
        extra={
            "error_type": exc.__class__.__name__,
            "context": context or {},
        },
    )
