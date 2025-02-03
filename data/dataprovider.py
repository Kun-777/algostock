from constants import Config
from pandas import DataFrame
from datetime import datetime, timezone
from constants import SymbolWithTimeframe
from exchange import Exchange

class DataProvider:
    def __init__(self, config: Config, exchange: Exchange | None, symbollists=None) -> None:
        self._config = config
        self._exchange = exchange
        self._symbollists = symbollists
        self.__cached_symbols: dict[SymbolWithTimeframe, tuple[DataFrame, datetime]] = {}

    def _set_cached_df(self, symbol: str, timeframe: str, dataframe: DataFrame) -> None:
        """
        Store cached Dataframe.
        Using private method as this should never be used by a user
        (but the class is exposed via `self.dp` to the strategy)
        :param symbol: symbol to get the data for
        :param timeframe: Timeframe to get data for
        :param dataframe: analyzed dataframe
        """
        symbol_key = (symbol, timeframe)
        self.__cached_symbols[symbol_key] = (dataframe, datetime.now(timezone.utc))

    def _emit_df(self, symbol_key: SymbolWithTimeframe, dataframe: DataFrame, new_candle: bool) -> None:
        """
        Send this dataframe as an ANALYZED_DF message to RPC

        :param symbol_key: SymbolWithTimeframe tuple
        :param dataframe: Dataframe to emit
        :param new_candle: This is a new candle
        """
        pass
        # if self.__rpc:
        #     msg: RPCAnalyzedDFMsg = {
        #         "type": RPCMessageType.ANALYZED_DF,
        #         "data": {
        #             "key": pair_key,
        #             "df": dataframe.tail(1),
        #             "la": datetime.now(timezone.utc),
        #         },
        #     }
        #     self.__rpc.send_msg(msg)
        #     if new_candle:
        #         self.__rpc.send_msg(
        #             {
        #                 "type": RPCMessageType.NEW_CANDLE,
        #                 "data": pair_key,
        #             }
        #         )

    def ohlcv(self, symbol: str, timeframe: str | None = None, copy: bool = True) -> DataFrame:
        """
        Get candle (OHLCV) data for the given symbol as DataFrame
        Please use the `available_symbols` method to verify which symbols are currently cached.
        :param symbol: symbol to get the data for
        :param timeframe: Timeframe to get data for
        :param copy: copy dataframe before returning if True.
                     Use False only for read-only operations (where the dataframe is not modified)
        """

        return self._exchange.klines(
            (symbol, timeframe or self._config["timeframe"]), copy=copy
        )