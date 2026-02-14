import logging
import MetaTrader5 as mt5
import pandas as pd
from typing import List
from prop_watchlist import WATCHLIST  # your ticker list

logger = logging.getLogger(__name__)

# ------------------------
# Data Provider Functions
# ------------------------
def get_data(symbol, timeframe=mt5.TIMEFRAME_D1, count=250):
    """
    Fetches historical data from MT5 and returns a pandas DataFrame.
    """
    rates = mt5.copy_rates_from_pos(symbol, timeframe, 0, count)
    if rates is None or len(rates) == 0:
        return pd.DataFrame()

    df = pd.DataFrame(rates)
    df['timestamp'] = pd.to_datetime(df['time'], unit='s')
    return df


def get_universe() -> List[str]:
    """
    Return the list of tickers to scan.
    Windows-safe logging (ASCII only).
    """
    try:
        tickers = WATCHLIST
        logger.info(f"[INFO] Loaded {len(tickers)} tickers from prop_watchlist.py")
        return tickers
    except Exception as e:
        logger.error(f"[ERROR] Failed to load tickers: {e}")
        return []

def get_account_info() -> dict:
    """
    Retrieve account info for drawdown checks or position sizing.
    Placeholder for actual MT5 or broker API call.
    """
    try:
        # Replace with actual API call to get account info
        account_info = {
            "balance": 100000,
            "equity": 100000,
            "margin": 0,
        }
        return account_info
    except Exception as e:
        logger.error(f"[ERROR] Could not retrieve account info: {e}")
        return {}
