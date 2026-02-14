import logging
from typing import List
from prop_watchlist import WATCHLIST  # your ticker list

logger = logging.getLogger(__name__)

# ------------------------
# Data Provider Functions
# ------------------------
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
