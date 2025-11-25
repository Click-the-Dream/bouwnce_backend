from datetime import datetime, timedelta

def build_date_filter(range_type: str, start_date=None, end_date=None):
    today = datetime.utcnow().date()


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
