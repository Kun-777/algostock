from datetime import datetime

from models.order import Order
from util import Precise

class Trade:
    id: int
    orders: list[Order]
    symbol: str
    is_open: bool
    open_rate: float
    open_trade_value: float | None = None
    close_rate: float | None = None
    close_profit: float | None = None
    amount: float
    open_date: datetime
    close_date: datetime | None = None
    stop_loss: float
    stop_loss_pct: float | None = None
    # absolute value of the highest reached price
    max_rate: float = None
    # Lowest price reached
    min_rate: float = None
    exit_reason: str = None
    exit_order_status: str = None
    strategy: str = None
    enter_tag: str = None
    leverage: int = 1
    is_short: bool = False
    liquidation_price: float = None

    def calc_profit_ratio(
        self, rate: float, amount: float | None = None, open_rate: float | None = None
    ) -> float:
        """
        Calculates the profit as ratio (including fee).
        :param rate: rate to compare with.
        :param amount: Amount to use for the calculation. Falls back to trade.amount if not set.
        :param open_rate: open_rate to use. Defaults to self.open_rate if not provided.
        :return: profit ratio as float
        """
        close_trade_value = Precise(rate) * Precise(amount)

        if amount is None or open_rate is None:
            open_trade_value = self.open_trade_value
        else:
            open_trade_value = Precise(amount) * Precise(open_rate)

        if open_trade_value == 0.0:
            return 0.0
        else:
            if self.is_short:
                profit_ratio = (1 - (close_trade_value / open_trade_value)) * self.leverage
            else:
                profit_ratio = ((close_trade_value / open_trade_value) - 1) * self.leverage

        return float(f"{profit_ratio:.8f}")

    def adjust_min_max_rates(self, current_price: float, current_price_low: float) -> None:
        """
        Adjust the max_rate and min_rate.
        """
        self.max_rate = max(current_price, self.max_rate or self.open_rate)
        self.min_rate = min(current_price_low, self.min_rate or self.open_rate)