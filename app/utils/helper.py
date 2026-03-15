import re
import secrets
import string
import uuid
from datetime import UTC, date, datetime, timedelta

UTC = UTC


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

    raise ValueError(f"Unsupported duration unit: {unit}")


def compute_remaining_time(time: datetime) -> float:

    now = datetime.now(UTC)

    remaining_time_seconds = (time - now).total_seconds()

    return max(0, remaining_time_seconds)


def generate_track_id() -> str:
    alphabet = string.ascii_letters + string.digits

    track_id = "".join(secrets.choice(alphabet) for _ in range(15))
    return track_id


def generate_order_track_id():
    return f"#ord-{generate_track_id()}"


def generate_suborder_track_id():
    return f"#subord-{generate_order_track_id()}"
