from alpaca.data.timeframe import TimeFrame, TimeFrameUnit
from exceptions import ConfigurationError

def alpaca_parse_timeframe(timeframe: str) -> TimeFrame:
    """
    parse timeframe to alpaca TimeFrame object

    :param timeframe: Timeframe string (E.g. 5m, 4h)
    """
    amount = int(timeframe[0:-1])
    unit = timeframe[-1]
    if 'M' == unit:
        alpaca_unit = TimeFrameUnit.Month
    elif 'w' == unit:
        alpaca_unit = TimeFrameUnit.Week
    elif 'd' == unit:
        alpaca_unit = TimeFrameUnit.Day
    elif 'h' == unit:
        alpaca_unit = TimeFrameUnit.Hour
    elif 'm' == unit:
        alpaca_unit = TimeFrameUnit.Minute
    else:
        raise ConfigurationError('timeframe unit {} is not supported'.format(unit))
    try:
        alpaca_tf = TimeFrame(amount, alpaca_unit)
    except ValueError:
        raise ConfigurationError(f'timeframe {timeframe} is not supported by Alpaca')
    return alpaca_tf