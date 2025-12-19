import re
import uuid
from datetime import UTC, datetime, timedelta


def build_date_filter(range_type: str, start_date=None, end_date=None):
    today = datetime.now(UTC).date()

    if isinstance(start_date, str):
        start_date = datetime.strptime(start_date, "%Y-%m-%d").date()

    if isinstance(end_date, str):
        end_date = datetime.strptime(end_date, "%Y-%m-%d").date()

    if range_type == "yesterday":
        start = today - timedelta(days=1)
        end = start

    elif range_type == "last_7_days":
        start = today - timedelta(days=7)
        end = today

    elif range_type == "last_30_days":
        start = today - timedelta(days=30)
        end = today

    elif range_type == "this_month":
        start = today.replace(day=1)
        end = today

    elif range_type == "custom":
        if not start_date or not end_date:
            raise ValueError("start_date and end_date are required for custom range")
        start, end = start_date, end_date

    else:
        raise ValueError(f"Invalid date range type: {range_type}")

    return start, end


def is_valid_uuid(value: str) -> bool:
    try:
        uuid_obj = uuid.UUID(str(value))
        return str(uuid_obj) == value.lower()
    except (ValueError, TypeError):
        return False


_DURATION_RE = re.compile(r"^(?P<value>\d+)(?P<unit>[smhd])$")


def parse_duration(duration: str) -> timedelta:
    """
    Convert a duration string like 15m, 7d 10s to timedelta object from datetime
    """

    if not isinstance(duration, str):
        raise ValueError("Duration must be a string")

    match = _DURATION_RE.match(duration.strip().lower())
    if not match:
        raise ValueError(
            "Invalid duration format. Expected format: <value><unit> e.g. 10s, 7d"
        )

    value = int(match.group("value"))
    unit = match.group("unit")

    if unit == "s":
        return timedelta(seconds=value)
    elif unit == "m":
        return timedelta(minutes=value)
    elif unit == "h":
        return timedelta(hours=value)
    elif unit == "d":
        return timedelta(days=value)

    return ValueError(f"Unsupported duration unit: {unit}")


def compute_remaining_time(time: datetime) -> float:

    now = datetime.now(UTC)

    remaining_time_seconds = (time - now).total_seconds()

    return max(0, remaining_time_seconds)
