import argparse
import csv
import json
import logging
import sys
from datetime import datetime, time
from pathlib import Path

import MetaTrader5 as mt5
import pandas as pd

from config import *
from risk_management import is_drawdown_safe, is_earnings_safe, get_current_currency_exposure, is_market_open, is_instrument_enabled
from mt5_news_filter import is_trading_blocked
from utils import get_symbol_category
from data_provider import get_data
from trade_executor import execute_mt5_trade, close_position_and_orders
from strategies import run_entry_scan, run_exit_scan
# Import Watchlist
from prop_watchlist import WATCHLIST

src_folder = Path(__file__).resolve().parent
env_path = src_folder / '.env'

load_dotenv(dotenv_path=env_path)

logger = logging.getLogger("MT5MasterControl")

FALLBACK_WATCHLIST = [
    'GBPNZD', 'GBPJPY', 'EURNZD', 'CHFJPY', 'GBPAUD', 'GBPAUD', 'GBPCAD', 'GBPCHF', 'NZDJPY', 'EURCAD',
    'CADJPY', 'AUDNZD', 'AUDJPY', 'USDCHF', 'NZDCHF', 'EURAUD', 'AUDCAD', 'NZDCAD', 'EURCHF', 'AUDCHF',
    'USDJPY', 'USDCAD', 'NZDUSD', 'GBPUSD', 'EURUSD', 'EURJPY', 'CADCHF', 'AUDUSD',
]


def initialize_mt5():
    """Initializes MT5 using credentials from .env"""
    # Use the logic from your mt5_test.py here
    login = int(os.getenv("MT5_LOGIN"))
    password = os.getenv("MT5_PASSWORD")
    server = os.getenv("MT5_SERVER")

    if not mt5.initialize(login=login, password=password, server=server):
        logger.error(f"Failed to initialize MT5: {mt5.last_error()}")
        sys.exit(1)
    logger.info(f"Connected to MT5: {mt5.account_info().login}")


def mt5_shutdown():
    mt5.shutdown()

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='MT5 Forex Sid Method Trading Bot')
    parser.add_argument('--mode', type=str, required=True, choices=['entry', 'exit', 'trail'],
                        help='entry: daily scan, exit: RSI targets, trail: move stop losses')

    # Optional switches to disable categories via command line
    parser.add_argument('--no-stocks', action='store_true', help='Disable Stock trading')
    parser.add_argument('--no-crypto', action='store_true', help='Disable Crypto trading')
    parser.add_argument('--no-forex', action='store_true', help='Disable Forex trading')

    args = parser.parse_args()

    # Apply CLI overrides to TRADE_SETTINGS
    if args.no_stocks: TRADE_SETTINGS["STOCKS"] = False
    if args.no_crypto: TRADE_SETTINGS["CRYPTO"] = False
    if args.no_forex:  TRADE_SETTINGS["FOREX"] = False

    try:
        initialize_mt5()

        # --- EXECUTION MODES ---
        if args.mode == 'trail':
            # Fast check: Move stop losses based on ATR volatility
            logger.info(f"[{datetime.now().strftime('%H:%M:%S')}] Running Trailing Stop Update...")
            apply_trailing_stop()

        elif args.mode == 'exit':
            # Hourly check: Close positions if RSI crosses 50
            logger.info(f"[{datetime.now().strftime('%H:%M:%S')}] Running RSI Exit Scan...")
            run_exit_scan()

        elif args.mode == 'entry':
            # Daily check: Find new trade setups
            run_entry_scan()

    except Exception as e:
        logger.error(f"An error occurred: {e}")
    finally:
        mt5_shutdown()
        logger.info("MT5 connection closed.")

