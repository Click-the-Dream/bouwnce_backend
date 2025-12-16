import uuid
from datetime import UTC, datetime, timedelta

from datetime import datetime, timedelta, date, timezone

UTC = timezone.utc


def build_date_filter(
    range_type: str,
    start_date: str | date | None = None,
    end_date: str | date | None = None,
) -> tuple[date, date]:
    today = datetime.now(UTC).date()

    if isinstance(start_date, str):
        start_date = datetime.strptime(start_date, "%Y-%m-%d").date()

    if isinstance(end_date, str):
        end_date = datetime.strptime(end_date, "%Y-%m-%d").date()

    match range_type:
        case "today":
            start = end = today

        case "yesterday":
            start = end = today - timedelta(days=1)

        case "last_7_days":
            # Includes today → today + previous 6 days
            start = today - timedelta(days=6)
            end = today

        case "last_30_days":
            # Includes today → today + previous 29 days
            start = today - timedelta(days=29)
            end = today

        case "this_month":
            start = today.replace(day=1)
            end = today

        case "custom":
            if not start_date or not end_date:
                raise ValueError(
                    "start_date and end_date are required for custom range"
                )

            if start_date > end_date:
                raise ValueError("start_date cannot be after end_date")

            start, end = start_date, end_date

        case _:
            raise ValueError(f"Invalid date range type: {range_type}")

    return start, end

def is_valid_uuid(value: str) -> bool:
    try:
        uuid_obj = uuid.UUID(str(value))
        return str(uuid_obj) == value.lower()
    except (ValueError, TypeError):
        return False
