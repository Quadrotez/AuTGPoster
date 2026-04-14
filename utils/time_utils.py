from datetime import datetime, timedelta, timezone as tz


def parse_datetime(text: str, tz_offset: float) -> datetime | None:
    text = text.strip()
    try:
        if len(text.split()) == 2:
            dt_local = datetime.strptime(text, "%H:%M %d.%m.%Y")
        else:
            time_only = datetime.strptime(text, "%H:%M")
            now_local = datetime.now(tz.utc) + timedelta(hours=tz_offset)
            dt_local = now_local.replace(
                hour=time_only.hour, minute=time_only.minute,
                second=0, microsecond=0, tzinfo=None
            )
            if dt_local <= now_local.replace(tzinfo=None):
                dt_local += timedelta(days=1)
        return dt_local - timedelta(hours=tz_offset)
    except ValueError:
        return None
