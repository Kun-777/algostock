"""
bot constants
"""

from typing import Any, Literal

DEFAULT_CONFIG = "config.json"
DRY_RUN_WALLET = 10000

MINIMAL_CONFIG = {
    "dry_run": True,
    "alpaca_key": "",
    "alpaca_secret": ""
}

CANCEL_REASON = {
    "TIMEOUT": "cancelled due to timeout",
    "PARTIALLY_FILLED_KEEP_OPEN": "partially filled - keeping order open",
    "PARTIALLY_FILLED": "partially filled",
    "FULLY_CANCELLED": "fully cancelled",
    "ALL_CANCELLED": "cancelled (all unfilled and partially filled open orders cancelled)",
    "CANCELLED_ON_EXCHANGE": "cancelled on exchange",
    "FORCE_EXIT": "forcesold",
    "REPLACE": "cancelled to be replaced by new limit order",
    "REPLACE_FAILED": "failed to replace order, deleting Trade",
    "USER_CANCEL": "user requested order cancel",
}

LongShort = Literal["long", "short"]
EntryExit = Literal["entry", "exit"]
BuySell = Literal["buy", "sell"]
Config = dict[str, Any]
IntOrInf = float