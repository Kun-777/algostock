from datetime import datetime
from zoneinfo import ZoneInfo
from time import time



def dt_now() -> datetime:
    """Return the current datetime in NYC Timezone."""
    return datetime.now(ZoneInfo("America/New_York"))

def dt_ts(dt: datetime | None = None) -> int:
    """
    Return dt in ms as a timestamp.
    If dt is None, return the current datetime.
    """
    if dt:
        return int(dt.timestamp() * 1000)
    return int(time() * 1000)

def dt_from_ts(timestamp: float) -> datetime:
    """
    Return a datetime from a timestamp.
    :param timestamp: timestamp in seconds or milliseconds
    """
    if timestamp > 1e10:
        # Timezone in ms - convert to seconds
        timestamp /= 1000
    return datetime.fromtimestamp(timestamp, tz=ZoneInfo("America/New_York"))
