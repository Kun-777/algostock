import logging
from abc import ABC, abstractmethod
from constants import IntOrInf, Config, CUSTOM_TAG_MAX_LENGTH
from datetime import datetime, timedelta, timezone
from pandas import DataFrame

from enums import SignalType, SignalTagType, SignalDirection, ExitType, ExitCheckTuple
from exceptions import StrategyError
from models import Trade, Order
from strategy.strategy_wrapper import strategy_safe_wrapper
from misc import remove_entry_exit_signals
from util import dt_now, timeframe_to_minutes, timeframe_to_seconds

logger = logging.getLogger(__name__)

class IStrategy(ABC):
    # associated minimal roi
    minimal_roi: dict = {}

    # associated stoploss
    stoploss: float

    # max open trades for the strategy
    max_open_trades: IntOrInf

    # Can this strategy go short?
    can_short: bool = False

    # associated timeframe
    timeframe: str

    # run "populate_indicators" only for new candle
    process_only_new_candles: bool = True

    use_exit_signal: bool
    exit_profit_only: bool
    exit_profit_offset: float
    ignore_roi_if_entry_signal: bool

    # Number of seconds after which the candle will no longer result in a buy on expired candles
    ignore_buying_expired_candle_after: int = 0

    # Disable checking the dataframe (converts the error into a warning message)
    disable_dataframe_checks: bool = False

    # Count of candles the strategy requires before producing valid signals
    startup_candle_count: int = 0

    dp: DataProvider

    def __init__(self, config: Config) -> None:
        self.config = config
        self._last_candle_seen_per_symbol: dict[str, datetime] = {}

    def as_bot_start(self, **kwargs) -> None:
        """
        Strategy init - runs after dataprovider has been added.
        Must call bot_start()
        """

        strategy_safe_wrapper(self.bot_start)()

    @abstractmethod
    def populate_indicators(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        """
        Populate indicators that will be used in the Buy, Sell, Short, Exit_short strategy
        :param dataframe: DataFrame with data from the exchange
        :param metadata: Additional information, like the currently traded symbol
        :return: a Dataframe with all mandatory indicators for the strategies
        """
        return dataframe

    def populate_entry_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        """
        Based on TA indicators, populates the entry signal for the given dataframe
        :param dataframe: DataFrame
        :param metadata: Additional information, like the currently traded symbol
        :return: DataFrame with entry columns populated
        """
        return dataframe

    def populate_exit_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        """
        Based on TA indicators, populates the exit signal for the given dataframe
        :param dataframe: DataFrame
        :param metadata: Additional information, like the currently traded symbol
        :return: DataFrame with exit columns populated
        """
        return dataframe

    def bot_start(self, **kwargs) -> None:
        """
        Called only once after bot instantiation.
        :param **kwargs: Ensure to keep this here so updates to this won't break your strategy.
        """
        pass

    def bot_loop_start(self, current_time: datetime, **kwargs) -> None:
        """
        Called at the start of the bot iteration (one loop).
        Might be used to perform symbol-independent tasks
        (e.g. gather some remote resource for comparison)
        :param current_time: datetime object, containing the current datetime
        :param **kwargs: Ensure to keep this here so updates to this won't break your strategy.
        """
        pass

    def check_entry_timeout(
        self, symbol: str, trade: Trade, order: Order, current_time: datetime, **kwargs
    ) -> bool:
        """
        Check entry timeout function callback.
        This method can be used to override the entry-timeout.
        It is called whenever a limit entry order has been created,
        and is not yet fully filled.
        Configuration options in `unfilledtimeout` will be verified before this,
        so ensure to set these timeouts high enough.

        When not implemented by a strategy, this simply returns False.
        :param symbol: Symbol the trade is for
        :param trade: Trade object.
        :param order: Order object.
        :param current_time: datetime object, containing the current datetime
        :param **kwargs: Ensure to keep this here so updates to this won't break your strategy.
        :return bool: When True is returned, then the entry order is cancelled.
        """
        return False
    
    def check_exit_timeout(
        self, symbol: str, trade: Trade, order: Order, current_time: datetime, **kwargs
    ) -> bool:
        """
        Check exit timeout function callback.
        This method can be used to override the exit-timeout.
        It is called whenever a limit exit order has been created,
        and is not yet fully filled.
        Configuration options in `unfilledtimeout` will be verified before this,
        so ensure to set these timeouts high enough.

        When not implemented by a strategy, this simply returns False.
        :param symbol: Symbol the trade is for
        :param trade: Trade object.
        :param order: Order object
        :param current_time: datetime object, containing the current datetime
        :param **kwargs: Ensure to keep this here so updates to this won't break your strategy.
        :return bool: When True is returned, then the exit-order is cancelled.
        """
        return False
    
    def confirm_trade_entry(
        self,
        symbol: str,
        order_type: str,
        amount: float,
        rate: float,
        time_in_force: str,
        current_time: datetime,
        entry_tag: str | None,
        side: str,
        **kwargs,
    ) -> bool:
        """
        Called right before placing a entry order.
        Timing for this function is critical, so avoid doing heavy computations or
        network requests in this method.

        When not implemented by a strategy, returns True (always confirming).

        :param symbol: Symbol that's about to be bought/shorted.
        :param order_type: Order type (as configured in order_types). usually limit or market.
        :param amount: Amount in target (base) currency that's going to be traded.
        :param rate: Rate that's going to be used when using limit orders
                     or current rate for market orders.
        :param time_in_force: Time in force. Defaults to GTC (Good-til-cancelled).
        :param current_time: datetime object, containing the current datetime
        :param entry_tag: Optional entry_tag (buy_tag) if provided with the buy signal.
        :param side: 'long' or 'short' - indicating the direction of the proposed trade
        :param **kwargs: Ensure to keep this here so updates to this won't break your strategy.
        :return bool: When True is returned, then the buy-order is placed on the exchange.
            False aborts the process
        """
        return True

    def confirm_trade_exit(
        self,
        symbol: str,
        trade: Trade,
        order_type: str,
        amount: float,
        rate: float,
        time_in_force: str,
        exit_reason: str,
        current_time: datetime,
        **kwargs,
    ) -> bool:
        """
        Called right before placing a regular exit order.
        Timing for this function is critical, so avoid doing heavy computations or
        network requests in this method.

        When not implemented by a strategy, returns True (always confirming).

        :param symbol: Symbol for trade that's about to be exited.
        :param trade: trade object.
        :param order_type: Order type (as configured in order_types). usually limit or market.
        :param amount: Amount in base currency.
        :param rate: Rate that's going to be used when using limit orders
                     or current rate for market orders.
        :param time_in_force: Time in force. Defaults to GTC (Good-til-cancelled).
        :param exit_reason: Exit reason.
            Can be any of ['roi', 'stop_loss', 'stoploss_on_exchange', 'trailing_stop_loss',
                           'exit_signal', 'force_exit', 'emergency_exit']
        :param current_time: datetime object, containing the current datetime
        :param **kwargs: Ensure to keep this here so updates to this won't break your strategy.
        :return bool: When True, then the exit-order is placed on the exchange.
            False aborts the process
        """
        return True
    
    def order_filled(
        self, symbol: str, trade: Trade, order: Order, current_time: datetime, **kwargs
    ) -> None:
        """
        Called right after an order fills.
        Will be called for all order types (entry, exit, stoploss, position adjustment).
        :param symbol: Symbol for trade
        :param trade: trade object.
        :param order: Order object.
        :param current_time: datetime object, containing the current datetime
        :param **kwargs: Ensure to keep this here so updates to this won't break your strategy.
        """
        pass

    def custom_stoploss(
        self,
        symbol: str,
        trade: Trade,
        current_time: datetime,
        current_rate: float,
        current_profit: float,
        after_fill: bool,
        **kwargs,
    ) -> float | None:
        """
        Custom stoploss logic, returning the new distance relative to current_rate (as ratio).
        e.g. returning -0.05 would create a stoploss 5% below current_rate.
        The custom stoploss can never be below self.stoploss, which serves as a hard maximum loss.

        When not implemented by a strategy, returns the initial stoploss value.
        Only called when use_custom_stoploss is set to True.

        :param symbol: Symbol that's currently analyzed
        :param trade: trade object.
        :param current_time: datetime object, containing the current datetime
        :param current_rate: Rate, calculated based on pricing settings in exit_pricing.
        :param current_profit: Current profit (as ratio), calculated based on current_rate.
        :param after_fill: True if the stoploss is called after the order was filled.
        :param **kwargs: Ensure to keep this here so updates to this won't break your strategy.
        :return float: New stoploss value, relative to the current_rate
        """
        return self.stoploss

    def custom_entry_price(
        self,
        symbol: str,
        trade: Trade | None,
        current_time: datetime,
        proposed_rate: float,
        entry_tag: str | None,
        side: str,
        **kwargs,
    ) -> float:
        """
        Custom entry price logic, returning the new entry price.

        When not implemented by a strategy, returns None, orderbook is used to set entry price

        :param symbol: Symbol that's currently analyzed
        :param trade: trade object (None for initial entries).
        :param current_time: datetime object, containing the current datetime
        :param proposed_rate: Rate, calculated based on pricing settings in exit_pricing.
        :param entry_tag: Optional entry_tag (buy_tag) if provided with the buy signal.
        :param side: 'long' or 'short' - indicating the direction of the proposed trade
        :param **kwargs: Ensure to keep this here so updates to this won't break your strategy.
        :return float: New entry price value if provided
        """
        return proposed_rate
    
    def custom_exit_price(
        self,
        symbol: str,
        trade: Trade,
        current_time: datetime,
        proposed_rate: float,
        current_profit: float,
        exit_tag: str | None,
        **kwargs,
    ) -> float:
        """
        Custom exit price logic, returning the new exit price.

        When not implemented by a strategy, returns None, orderbook is used to set exit price

        :param symbol: Symbol that's currently analyzed
        :param trade: trade object.
        :param current_time: datetime object, containing the current datetime
        :param proposed_rate: Rate, calculated based on pricing settings in exit_pricing.
        :param current_profit: Current profit (as ratio), calculated based on current_rate.
        :param exit_tag: Exit reason.
        :param **kwargs: Ensure to keep this here so updates to this won't break your strategy.
        :return float: New exit price value if provided
        """
        return proposed_rate
    
    def custom_exit(
        self,
        symbol: str,
        trade: Trade,
        current_time: datetime,
        current_rate: float,
        current_profit: float,
        **kwargs,
    ) -> str | bool | None:
        """
        Custom exit signal logic indicating that specified position should be sold. Returning a
        string or True from this method is equal to setting exit signal on a candle at specified
        time. This method is not called when exit signal is set.

        This method should be overridden to create exit signals that depend on trade parameters. For
        example you could implement an exit relative to the candle when the trade was opened,
        or a custom 1:2 risk-reward ROI.

        Custom exit reason max length is 64. Exceeding characters will be removed.

        :param symbol: Symbol that's currently analyzed
        :param trade: trade object.
        :param current_time: datetime object, containing the current datetime
        :param current_rate: Rate, calculated based on pricing settings in exit_pricing.
        :param current_profit: Current profit (as ratio), calculated based on current_rate.
        :param **kwargs: Ensure to keep this here so updates to this won't break your strategy.
        :return: To execute exit, return a string with custom exit reason or True. Otherwise return
        None or False.
        """
        return None
    
    def get_strategy_name(self) -> str:
        """
        Returns strategy class name
        """
        return self.__class__.__name__
    
    def analyze_ticker(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        """
        Parses the given candle (OHLCV) data and returns a populated DataFrame
        add several TA indicators and entry order signal to it
        Should only be used in live.
        :param dataframe: Dataframe containing data from exchange
        :param metadata: Metadata dictionary with additional data (e.g. 'symbol')
        :return: DataFrame of candle (OHLCV) data with indicator data and signals added
        """
        logger.debug("TA Analysis Launched")
        dataframe = self.advise_indicators(dataframe, metadata)
        dataframe = self.advise_entry(dataframe, metadata)
        dataframe = self.advise_exit(dataframe, metadata)
        logger.debug("TA Analysis Ended")
        return dataframe
    
    def _analyze_ticker_internal(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        """
        Parses the given candle (OHLCV) data and returns a populated DataFrame
        add several TA indicators and buy signal to it
        WARNING: Used internally only, may skip analysis if `process_only_new_candles` is set.
        :param dataframe: Dataframe containing data from exchange
        :param metadata: Metadata dictionary with additional data (e.g. 'symbol')
        :return: DataFrame of candle (OHLCV) data with indicator data and signals added
        """
        symbol = str(metadata.get("symbol"))

        new_candle = self._last_candle_seen_per_symbol.get(symbol, None) != dataframe.iloc[-1]["date"]
        # Test if seen this symbol and last candle before.
        # always run if process_only_new_candles is set to false
        if not self.process_only_new_candles or new_candle:
            # Defs that only make change on new candle data.
            dataframe = self.analyze_ticker(dataframe, metadata)

            self._last_candle_seen_per_symbol[symbol] = dataframe.iloc[-1]["date"]

            self.dp._set_cached_df(symbol, self.timeframe, dataframe)
            self.dp._emit_df((symbol, self.timeframe), dataframe, new_candle)

        else:
            logger.debug("Skipping TA Analysis for already analyzed candle")
            dataframe = remove_entry_exit_signals(dataframe)

        logger.debug("Loop Analysis Launched")

        return dataframe
    
    def analyze_symbol(self, symbol: str) -> None:
        """
        Fetch data for this symbol from dataprovider and analyze.
        Stores the dataframe into the dataprovider.
        The analyzed dataframe is then accessible via `dp.get_analyzed_dataframe()`.
        :param symbol: Symbol to analyze.
        """
        dataframe = self.dp.ohlcv(
            symbol, self.timeframe
        )
        if not isinstance(dataframe, DataFrame) or dataframe.empty:
            logger.warning("Empty candle (OHLCV) data for symbol %s", symbol)
            return

        try:
            df_len, df_close, df_date = self.preserve_df(dataframe)

            dataframe = strategy_safe_wrapper(self._analyze_ticker_internal, message="")(
                dataframe, {"symbol": symbol}
            )

            self.assert_df(dataframe, df_len, df_close, df_date)
        except StrategyError as error:
            logger.warning(f"Unable to analyze candle (OHLCV) data for symbol {symbol}: {error}")
            return

        if dataframe.empty:
            logger.warning("Empty dataframe for symbol %s", symbol)
            return
        
    def analyze(self, symbols: list[str]) -> None:
        """
        Analyze all symbols using analyze_symbol().
        :param symbols: List of symbols to analyze
        """
        for symbol in symbols:
            self.analyze_symbol(symbol)

    @staticmethod
    def preserve_df(dataframe: DataFrame) -> tuple[int, float, datetime]:
        """keep some data for dataframes"""
        return len(dataframe), dataframe["close"].iloc[-1], dataframe["date"].iloc[-1]
    
    def assert_df(self, dataframe: DataFrame, df_len: int, df_close: float, df_date: datetime):
        """
        Ensure dataframe (length, last candle) was not modified, and has all elements we need.
        """
        message_template = "Dataframe returned from strategy has mismatching {}."
        message = ""
        if dataframe is None:
            message = "No dataframe returned (return statement missing?)."
        elif df_len != len(dataframe):
            message = message_template.format("length")
        elif df_close != dataframe["close"].iloc[-1]:
            message = message_template.format("last close price")
        elif df_date != dataframe["date"].iloc[-1]:
            message = message_template.format("last date")
        if message:
            if self.disable_dataframe_checks:
                logger.warning(message)
            else:
                raise StrategyError(message)
            
    def get_latest_candle(
        self,
        symbol: str,
        timeframe: str,
        dataframe: DataFrame,
    ) -> tuple[DataFrame | None, datetime | None]:
        """
        Calculates current signal based based on the entry order or exit order
        columns of the dataframe.
        Used by Bot to get the signal to enter, or exit
        :param symbol: Symbol in format ANT/BTC
        :param timeframe: timeframe to use
        :param dataframe: Analyzed dataframe to get signal from.
        :return: (None, None) or (Dataframe, latest_date) - corresponding to the last candle
        """
        if not isinstance(dataframe, DataFrame) or dataframe.empty:
            logger.warning(f"Empty candle (OHLCV) data for symbol {symbol}")
            return None, None

        try:
            latest_date_pd = dataframe["date"].max()
            latest = dataframe.loc[dataframe["date"] == latest_date_pd].iloc[-1]
        except Exception as e:
            logger.warning(f"Unable to get latest candle (OHLCV) data for symbol {symbol} - {e}")
            return None, None
        # Explicitly convert to datetime object to ensure the below comparison does not fail
        latest_date: datetime = latest_date_pd.to_pydatetime()

        # Check if dataframe is out of date
        timeframe_minutes = timeframe_to_minutes(timeframe)
        offset = self.config.get("outdated_offset", 5)
        if latest_date < (dt_now() - timedelta(minutes=timeframe_minutes * 2 + offset)):
            logger.warning(
                "Outdated history for symbol %s. Last tick is %s minutes old",
                symbol,
                int((dt_now() - latest_date).total_seconds() // 60),
            )
            return None, None
        return latest, latest_date
    
    def get_exit_signal(
        self, symbol: str, timeframe: str, dataframe: DataFrame, is_short: bool | None = None
    ) -> tuple[bool, bool, str | None]:
        """
        Calculates current exit signal based based on the dataframe
        columns of the dataframe.
        Used by Bot to get the signal to exit.
        depending on is_short, looks at "short" or "long" columns.
        :param symbol: symbol to use
        :param timeframe: timeframe to use
        :param dataframe: Analyzed dataframe to get signal from.
        :param is_short: Indicating existing trade direction.
        :return: (enter, exit) A bool-tuple with enter / exit values.
        """
        latest, _latest_date = self.get_latest_candle(symbol, timeframe, dataframe)
        if latest is None:
            return False, False, None

        if is_short:
            enter = latest.get(SignalType.ENTER_SHORT.value, 0) == 1
            exit_ = latest.get(SignalType.EXIT_SHORT.value, 0) == 1

        else:
            enter = latest.get(SignalType.ENTER_LONG.value, 0) == 1
            exit_ = latest.get(SignalType.EXIT_LONG.value, 0) == 1
        exit_tag = latest.get(SignalTagType.EXIT_TAG.value, None)
        # Tags can be None, which does not resolve to False.
        exit_tag = exit_tag if isinstance(exit_tag, str) and exit_tag != "nan" else None

        logger.debug(f"exit-trigger: {latest['date']} (symbol={symbol}) enter={enter} exit={exit_}")

        return enter, exit_, exit_tag
    
    def get_entry_signal(
        self,
        symbol: str,
        timeframe: str,
        dataframe: DataFrame,
    ) -> tuple[SignalDirection | None, str | None]:
        """
        Calculates current entry signal based based on the dataframe signals
        columns of the dataframe.
        Used by Bot to get the signal to enter trades.
        :param symbol: symbol to use
        :param timeframe: timeframe to use
        :param dataframe: Analyzed dataframe to get signal from.
        :return: (SignalDirection, entry_tag)
        """
        latest, latest_date = self.get_latest_candle(symbol, timeframe, dataframe)
        if latest is None or latest_date is None:
            return None, None

        enter_long = latest.get(SignalType.ENTER_LONG.value, 0) == 1
        exit_long = latest.get(SignalType.EXIT_LONG.value, 0) == 1
        enter_short = latest.get(SignalType.ENTER_SHORT.value, 0) == 1
        exit_short = latest.get(SignalType.EXIT_SHORT.value, 0) == 1

        enter_signal: SignalDirection | None = None
        enter_tag: str | None = None
        if enter_long == 1 and not any([exit_long, enter_short]):
            enter_signal = SignalDirection.LONG
            enter_tag = latest.get(SignalTagType.ENTER_TAG.value, None)
        if (
            self.can_short
            and enter_short == 1
            and not any([exit_short, enter_long])
        ):
            enter_signal = SignalDirection.SHORT
            enter_tag = latest.get(SignalTagType.ENTER_TAG.value, None)

        enter_tag = enter_tag if isinstance(enter_tag, str) and enter_tag != "nan" else None

        timeframe_seconds = timeframe_to_seconds(timeframe)

        if self.ignore_expired_candle(
            latest_date=latest_date,
            current_time=dt_now(),
            timeframe_seconds=timeframe_seconds,
            enter=bool(enter_signal),
        ):
            return None, enter_tag

        logger.debug(
            f"entry trigger: {latest['date']} (symbol={symbol}) "
            f"enter={enter_long} enter_tag_value={enter_tag}"
        )
        return enter_signal, enter_tag
    
    def ignore_expired_candle(
        self, latest_date: datetime, current_time: datetime, timeframe_seconds: int, enter: bool
    ):
        if self.ignore_buying_expired_candle_after and enter:
            time_delta = current_time - (latest_date + timedelta(seconds=timeframe_seconds))
            return time_delta.total_seconds() > self.ignore_buying_expired_candle_after
        else:
            return False
        
    def should_exit(
        self,
        trade: Trade,
        rate: float,
        current_time: datetime,
        *,
        enter: bool,
        exit_: bool,
        low: float | None = None,
        high: float | None = None,
        force_stoploss: float = 0,
    ) -> list[ExitCheckTuple]:
        """
        This function evaluates if one of the conditions required to trigger an exit order
        has been reached, which can either be a stop-loss, ROI or exit-signal.
        :param low: Only used during backtesting to simulate (long)stoploss/(short)ROI
        :param high: Only used during backtesting, to simulate (short)stoploss/(long)ROI
        :param force_stoploss: Externally provided stoploss
        :return: List of exit reasons - or empty list.
        """
        exits: list[ExitCheckTuple] = []
        current_rate = rate
        current_profit = trade.calc_profit_ratio(current_rate)
        current_profit_best = current_profit
        if low is not None or high is not None:
            # Set current rate to high for backtesting ROI exits
            current_rate_best = (low if trade.is_short else high) or rate
            current_profit_best = trade.calc_profit_ratio(current_rate_best)

        trade.adjust_min_max_rates(high or current_rate, low or current_rate)

        stoplossflag = self.stoploss_reached(
            current_rate=current_rate,
            trade=trade,
            current_time=current_time,
            current_profit=current_profit,
            force_stoploss=force_stoploss,
            low=low,
            high=high,
        )

        # if enter signal and ignore_roi is set, we don't need to evaluate min_roi.
        roi_reached = not (enter and self.ignore_roi_if_entry_signal) and self.min_roi_reached(
            trade=trade, current_profit=current_profit_best, current_time=current_time
        )

        exit_signal = ExitType.NONE
        custom_reason = ""

        if self.use_exit_signal:
            if exit_ and not enter:
                exit_signal = ExitType.EXIT_SIGNAL
            else:
                reason_cust = strategy_safe_wrapper(self.custom_exit, default_retval=False)(
                    symbol=trade.symbol,
                    trade=trade,
                    current_time=current_time,
                    current_rate=current_rate,
                    current_profit=current_profit,
                )
                if reason_cust:
                    exit_signal = ExitType.CUSTOM_EXIT
                    if isinstance(reason_cust, str):
                        custom_reason = reason_cust
                        if len(reason_cust) > CUSTOM_TAG_MAX_LENGTH:
                            logger.warning(
                                f"Custom exit reason returned from "
                                f"custom_exit is too long and was trimmed"
                                f"to {CUSTOM_TAG_MAX_LENGTH} characters."
                            )
                            custom_reason = reason_cust[:CUSTOM_TAG_MAX_LENGTH]
                    else:
                        custom_reason = ""
            if exit_signal == ExitType.CUSTOM_EXIT or (
                exit_signal == ExitType.EXIT_SIGNAL
                and (not self.exit_profit_only or current_profit > self.exit_profit_offset)
            ):
                logger.debug(
                    f"{trade.symbol} - Sell signal received. "
                    f"exit_type=ExitType.{exit_signal.name}"
                    + (f", custom_reason={custom_reason}" if custom_reason else "")
                )
                exits.append(ExitCheckTuple(exit_type=exit_signal, exit_reason=custom_reason))

        # Sequence:
        # Exit-signal
        # Stoploss
        # ROI
        # Trailing stoploss

        if stoplossflag.exit_type in (ExitType.STOP_LOSS, ExitType.LIQUIDATION):
            logger.debug(f"{trade.symbol} - Stoploss hit. exit_type={stoplossflag.exit_type}")
            exits.append(stoplossflag)

        if roi_reached:
            logger.debug(f"{trade.symbol} - Required profit reached. exit_type=ExitType.ROI")
            exits.append(ExitCheckTuple(exit_type=ExitType.ROI))

        if stoplossflag.exit_type == ExitType.TRAILING_STOP_LOSS:
            logger.debug(f"{trade.symbol} - Trailing stoploss hit.")
            exits.append(stoplossflag)

        return exits
    
    def stoploss_reached(
        self,
        current_rate: float,
        trade: Trade,
        current_time: datetime,
        current_profit: float,
        force_stoploss: float,
        low: float | None = None,
        high: float | None = None,
    ) -> ExitCheckTuple:
        """
        Based on current profit of the trade and configured (trailing) stoploss,
        decides to exit or not
        :param current_profit: current profit as ratio
        :param low: Low value of this candle, only set in backtesting
        :param high: High value of this candle, only set in backtesting
        """
        # self.ft_stoploss_adjust(
        #     current_rate, trade, current_time, current_profit, force_stoploss, low, high
        # )

        sl_higher_long = trade.stop_loss >= (low or current_rate) and not trade.is_short
        sl_lower_short = trade.stop_loss <= (high or current_rate) and trade.is_short
        liq_higher_long = (
            trade.liquidation_price
            and trade.liquidation_price >= (low or current_rate)
            and not trade.is_short
        )
        liq_lower_short = (
            trade.liquidation_price
            and trade.liquidation_price <= (high or current_rate)
            and trade.is_short
        )

        # evaluate if the stoploss was hit if stoploss is not on exchange
        # in Dry-Run, this handles stoploss logic as well, as the logic will not be different to
        # regular stoploss handling.
        if (sl_higher_long or sl_lower_short) and (
            not self.order_types.get("stoploss_on_exchange") or self.config["dry_run"]
        ):
            exit_type = ExitType.STOP_LOSS

            # # If initial stoploss is not the same as current one then it is trailing.
            # if trade.is_stop_loss_trailing:
            #     exit_type = ExitType.TRAILING_STOP_LOSS
            #     logger.debug(
            #         f"{trade.symbol} - HIT STOP: current price at "
            #         f"{((high if trade.is_short else low) or current_rate):.6f}, "
            #         f"stoploss is {trade.stop_loss:.6f}, "
            #         f"initial stoploss was at {trade.initial_stop_loss:.6f}, "
            #         f"trade opened at {trade.open_rate:.6f}"
            #     )

            return ExitCheckTuple(exit_type=exit_type)

        if liq_higher_long or liq_lower_short:
            logger.debug(f"{trade.symbol} - Liquidation price hit. exit_type=ExitType.LIQUIDATION")
            return ExitCheckTuple(exit_type=ExitType.LIQUIDATION)

        return ExitCheckTuple(exit_type=ExitType.NONE)
    
    def min_roi_reached_entry(self, trade_dur: int) -> tuple[int | None, float | None]:
        """
        Based on trade duration defines the ROI entry that may have been reached.
        :param trade_dur: trade duration in minutes
        :return: minimal ROI entry value or None if none proper ROI entry was found.
        """
        # Get highest entry in ROI dict where key <= trade-duration
        roi_list = [x for x in self.minimal_roi.keys() if x <= trade_dur]
        if not roi_list:
            return None, None
        roi_entry = max(roi_list)
        return roi_entry, self.minimal_roi[roi_entry]

    def min_roi_reached(self, trade: Trade, current_profit: float, current_time: datetime) -> bool:
        """
        Based on trade duration, current profit of the trade and ROI configuration,
        decides whether bot should exit.
        :param current_profit: current profit as ratio
        :return: True if bot should exit at current rate
        """
        # Check if time matches and current rate is above threshold
        trade_dur = int((current_time.timestamp() - trade.open_date.timestamp()) // 60)
        _, roi = self.min_roi_reached_entry(trade_dur)
        if roi is None:
            return False
        else:
            return current_profit > roi
        
    def advise_indicators(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        """
        Populate indicators that will be used in the Buy, Sell, short, exit_short strategy
        This method should not be overridden.
        :param dataframe: Dataframe with data from the exchange
        :param metadata: Additional information, like the currently traded symbol
        :return: a Dataframe with all mandatory indicators for the strategies
        """
        logger.debug(f"Populating indicators for symbol {metadata.get('symbol')}.")

        # call populate_indicators_Nm() which were tagged with @informative decorator.
        # for inf_data, populate_fn in self._ft_informative:
        #     dataframe = _create_and_merge_informative_symbol(
        #         self, dataframe, metadata, inf_data, populate_fn
        #     )

        # self._if_enabled_populate_trades(dataframe, metadata)
        return self.populate_indicators(dataframe, metadata)

    def advise_entry(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        """
        Based on TA indicators, populates the entry order signal for the given dataframe
        This method should not be overridden.
        :param dataframe: DataFrame
        :param metadata: Additional information dictionary, with details like the
            currently traded symbol
        :return: DataFrame with buy column
        """

        logger.debug(f"Populating enter signals for symbol {metadata.get('symbol')}.")
        # Initialize column to work around Pandas bug #56503.
        dataframe.loc[:, "enter_tag"] = ""
        df = self.populate_entry_trend(dataframe, metadata)
        if "enter_long" not in df.columns:
            df = df.rename({"buy": "enter_long", "buy_tag": "enter_tag"}, axis="columns")

        return df

    def advise_exit(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        """
        Based on TA indicators, populates the exit order signal for the given dataframe
        This method should not be overridden.
        :param dataframe: DataFrame
        :param metadata: Additional information dictionary, with details like the
            currently traded symbol
        :return: DataFrame with exit column
        """
        # Initialize column to work around Pandas bug #56503.
        dataframe.loc[:, "exit_tag"] = ""
        logger.debug(f"Populating exit signals for symbol {metadata.get('symbol')}.")
        df = self.populate_exit_trend(dataframe, metadata)
        if "exit_long" not in df.columns:
            df = df.rename({"sell": "exit_long"}, axis="columns")
        return df