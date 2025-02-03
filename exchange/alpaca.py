from alpaca.data import StockHistoricalDataClient
from alpaca.data.requests import StockBarsRequest
from alpaca.trading.client import TradingClient
from alpaca.trading.requests import GetCalendarRequest
from datetime import datetime, timedelta
import pandas as pd

from exchange.exchange import Exchange
from constants import SymbolWithTimeframe
from util import timeframe_to_prev_prev_candle, timeframe_to_prev_candle, timeframe_to_resample_freq, dt_now
from exchange.alpaca_util import alpaca_parse_timeframe

class Alpaca(Exchange):

    def __init__(self, config):
        super().__init__(config)
        self.historical_data_client = StockHistoricalDataClient(self._config['alpaca_key'], self._config['alpaca_secret'])
        self.trading_client = TradingClient(self._config['alpaca_key'],  self._config['alpaca_secret'], paper=self._config['dry_run'])

    def get_calendar(self, date):
        if not date:
            date = dt_now().date()
        calendar_request_params = GetCalendarRequest(start=date, end=date)
        market_time = self.trading_client.get_calendar(calendar_request_params)
        for entry in market_time:
            self.calendar.update(date, {"open": entry.open, "close": entry.close})
        

    def get_ohlcv(self, symbol_interval: SymbolWithTimeframe) -> None:
        now = dt_now()
        symbol = symbol_interval[0]
        timeframe = symbol_interval[1]
        request_params = StockBarsRequest(symbol_or_symbols=symbol, 
                                          timeframe=alpaca_parse_timeframe(timeframe),
                                          start=timeframe_to_prev_prev_candle(timeframe, now),
                                          end=timeframe_to_prev_candle(timeframe, now) - timedelta(seconds=1))
        bars = self.historical_data_client.get_stock_bars(request_params).df
        
        if bars:
            market_hours_data = {}
            for symbol, group in bars.groupby(level='symbol'):
                df = group.reset_index(level='symbol').tz_convert('America/New_York', axis=0)
                market_hours_data[symbol] = df.reset_index().rename(columns={'timestamp': 'date'})
            if not self._klines:
                self._klines[symbol_interval] = market_hours_data[symbol]
            else:
                self._klines[symbol_interval] = pd.concat([self._klines[symbol_interval], market_hours_data[symbol]])
            self.fill_kline_gaps(symbol_interval)
    
    def fill_kline_gaps(self, symbol_interval) -> None:
        """
        Fill the gaps between candles, which could happen when no trades happen
        """
        df = self._klines[symbol_interval]
        start_date = df.index.min()
        valid_ts_subset = [ts for ts in self.valid_timestamps if ts >= start_date and ts < timeframe_to_prev_candle(symbol_interval[1], dt_now())]
        df = df[df.index.isin(valid_ts_subset)].reindex(valid_ts_subset)
        df.ffill(inplace=True)
