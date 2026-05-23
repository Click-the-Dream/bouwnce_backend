import logging
from collections.abc import Mapping
from typing import Any

logging.basicConfig(
    level=logging.ERROR,
    format="%(asctime)s - %(levelname)s - %(name)s - %(message)s",
)

logger = logging.getLogger("justclick")


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
