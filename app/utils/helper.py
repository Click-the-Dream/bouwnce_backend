import uuid
from datetime import datetime, timedelta
from app.utils.responses import response_builder

def is_valid_uuid(value: str) -> bool:
    try:
        uuid_obj = uuid.UUID(value)
        return str(uuid_obj) == value.lower()
    except (ValueError, TypeError):
        return False


def build_date_filter(range_type: str, start_date=None, end_date=None):
    today = datetime.utcnow().date()

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
        start = start_date
        end = end_date

    else:
        return response_builder(status_code=400, message="Invalid date range type")
    return start, end
