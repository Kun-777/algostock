import pandas as pd
from enums import SignalType, SignalTagType
from exceptions import ConfigurationError

def remove_entry_exit_signals(dataframe: pd.DataFrame):
    """
    Remove Entry and Exit signals from a DataFrame

    :param dataframe: The DataFrame to remove signals from
    """
    dataframe[SignalType.ENTER_LONG.value] = 0
    dataframe[SignalType.EXIT_LONG.value] = 0
    dataframe[SignalType.ENTER_SHORT.value] = 0
    dataframe[SignalType.EXIT_SHORT.value] = 0
    dataframe[SignalTagType.ENTER_TAG.value] = None
    dataframe[SignalTagType.EXIT_TAG.value] = None

    return dataframe

def parse_timeframe(timeframe):
    amount = int(timeframe[0:-1])
    unit = timeframe[-1]
    if 'y' == unit:
        scale = 60 * 60 * 24 * 365
    elif 'M' == unit:
        scale = 60 * 60 * 24 * 30
    elif 'w' == unit:
        scale = 60 * 60 * 24 * 7
    elif 'd' == unit:
        scale = 60 * 60 * 24
    elif 'h' == unit:
        scale = 60 * 60
    elif 'm' == unit:
        scale = 60
    elif 's' == unit:
        scale = 1
    else:
        raise ConfigurationError('timeframe unit {} is not supported'.format(unit))
    return amount * scale
