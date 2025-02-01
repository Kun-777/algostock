import logging
import os

# Logger
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger('Alpaca Trading Bot')
file_handler = logging.FileHandler('app.log')
file_handler.setLevel(logging.INFO)
formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
file_handler.setFormatter(formatter)
logger.addHandler(file_handler)

class AlgoStockBot():
    def __init__(self):
        alpaca_api_key = os.getenv("ALPACA_PAPER_API")
        alpaca_api_secret = os.getenv("ALPACA_PAPER_SECRET")
