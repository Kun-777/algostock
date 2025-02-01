from alpaca.data import StockHistoricalDataClient
from alpaca.data.live import StockDataStream
from alpaca.data.requests import StockBarsRequest
from alpaca.data.timeframe import TimeFrame, TimeFrameUnit
from alpaca.trading.client import TradingClient
from alpaca.trading.requests import GetCalendarRequest
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
import pandas as pd
from dotenv import load_dotenv
import os

def main():
    load_dotenv()
    alpaca_api_key = os.getenv("ALPACA_PAPER_KEY")
    alpaca_api_secret = os.getenv("ALPACA_PAPER_SECRET")

    # websocket approach

    # wss_client = StockDataStream(alpaca_api_key,  alpaca_api_secret)
    # async def bar_data_handler(data):
    #     print(data)

    # wss_client.subscribe_bars(bar_data_handler, "TSLA")
    # wss_client.run()

    # RESTFUL approach






if __name__ == "__main__":
    main()