import pandas as pd
from pandas import DataFrame
from pandas._libs.tslib import Timestamp
from datetime import datetime, date

from constants import Config, SymbolWithTimeframe
from util import dt_now, timeframe_to_resample_freq


class Exchange():
    def __init__(self, config: Config):
        self._config: Config = {}
        self._config.update(config)

        self._klines: dict[SymbolWithTimeframe, DataFrame] = {}

        self.calendar: dict[date, dict[str, datetime]] = {}
        self.valid_timestamps: list[Timestamp]
        self.valid_timestamps_today: list[Timestamp]

    def klines(self, symbol_interval: SymbolWithTimeframe, copy: bool = True) -> DataFrame:
        if symbol_interval in self._klines:
            return self._klines[symbol_interval].copy() if copy else self._klines[symbol_interval]
        else:
            return DataFrame()
        
    def get_calendar(self, date: date = None) -> None:
        pass

    def update_valid_timestamps(self, timeframe: str) -> None:
        market_time = self.calendar[dt_now().date()]
        timestamps = pd.date_range(start=market_time['open'], end=market_time['close'], inclusive='left', freq=timeframe_to_resample_freq(timeframe)).tz_localize('America/New_York')
        self.valid_timestamps.extend(timestamps)
        self.valid_timestamps_today = timestamps
        
    def get_ohlcv(self, symbol_interval: SymbolWithTimeframe) -> None:
        pass