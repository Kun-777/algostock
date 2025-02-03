from datetime import datetime, timezone

from misc import parse_timeframe
from util import dt_now, dt_ts, dt_from_ts

def timeframe_to_seconds(timeframe: str) -> int:
    """
    Translates the timeframe interval value written in the human readable
    form ('1m', '5m', '1h', '1d', '1w', etc.) to the number
    of seconds for one timeframe interval.
    """
    return parse_timeframe(timeframe)


def timeframe_to_minutes(timeframe: str) -> int:
    """
    Same as timeframe_to_seconds, but returns minutes.
    """
    return parse_timeframe(timeframe) // 60


def timeframe_to_msecs(timeframe: str) -> int:
    """
    Same as timeframe_to_seconds, but returns milliseconds.
    """
    return parse_timeframe(timeframe) * 1000

def timeframe_to_resample_freq(timeframe: str) -> str:
    """
    Translates the timeframe interval value written in the human readable
    form ('1m', '5m', '1h', '1d', '1w', etc.) to the resample frequency
    used by pandas ('1T', '5T', '1H', '1D', '1W', etc.)
    """
    if timeframe == "1y":
        return "1YS"
    timeframe_seconds = timeframe_to_seconds(timeframe)
    timeframe_minutes = timeframe_seconds // 60
    resample_interval = f"{timeframe_seconds}s"
    if 10000 < timeframe_minutes < 43200:
        resample_interval = "1W-MON"
    elif timeframe_minutes >= 43200 and timeframe_minutes < 525600:
        # Monthly candles need special treatment to stick to the 1st of the month
        resample_interval = f"{timeframe}S"
    elif timeframe_minutes > 43200:
        resample_interval = timeframe
    return resample_interval

def timeframe_to_prev_candle(timeframe: str, dt: datetime | None = None) -> datetime:
    """
    Use Timeframe and determine the candle start time for this datetime.
    Does not round when given a candle start time.
    :param timeframe: timeframe in string format (e.g. "5m")
    :param dt: datetime to use. Defaults to now(nyc timezone)
    :returns: datetime of previous candle (with nyc timezone)
    """
    if not dt:
        dt = dt_now()
    ms = timeframe_to_msecs(timeframe)
    timestamp = dt_ts(dt)
    # Get offset based on timeframe in milliseconds
    offset = timestamp % ms
    return dt_from_ts(timestamp - offset)

def timeframe_to_next_candle(timeframe: str, dt: datetime | None = None) -> datetime:
    """
    Use Timeframe and determine next candle.
    :param timeframe: timeframe in string format (e.g. "5m")
    :param dt: datetime to use. Defaults to now(nyc timezone)
    :returns: datetime of next candle (with nyc timezone)
    """
    if not dt:
        dt = dt_now()
    ms = timeframe_to_msecs(timeframe)
    timestamp = dt_ts(dt)
    # Get offset based on timeframe in milliseconds
    offset = timestamp % ms
    return dt_from_ts(timestamp - offset + ms)

def timeframe_to_prev_prev_candle(timeframe: str, dt: datetime | None = None) -> datetime:
    """
    Use Timeframe and determine the candle start time for this datetime.
    Does not round when given a candle start time.
    :param timeframe: timeframe in string format (e.g. "5m")
    :param dt: datetime to use. Defaults to now(nyc timezone)
    :returns: datetime of previous candle (with nyc timezone)
    """
    if not dt:
        dt = dt_now()
    ms = timeframe_to_msecs(timeframe)
    timestamp = dt_ts(dt)
    # Get offset based on timeframe in milliseconds
    offset = timestamp % ms
    return dt_from_ts(timestamp - offset - ms)