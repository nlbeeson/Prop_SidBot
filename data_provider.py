import MetaTrader5 as mt5
import pandas as pd
import logging
from prop_watchlist import WATCHLIST

logger = logging.getLogger("MT5MasterControl")

FALLBACK_WATCHLIST = [
    'GBPNZD', 'GBPJPY', 'EURNZD', 'CHFJPY', 'GBPAUD', 'GBPAUD', 'GBPCAD', 'GBPCHF', 'NZDJPY', 'EURCAD',
    'CADJPY', 'AUDNZD', 'AUDJPY', 'USDCHF', 'NZDCHF', 'EURAUD', 'AUDCAD', 'NZDCAD', 'EURCHF', 'AUDCHF',
    'USDJPY', 'USDCAD', 'NZDUSD', 'GBPUSD', 'EURUSD', 'EURJPY', 'CADCHF', 'AUDUSD',
]


def get_data(ticker):
    # Fetch 100 bars to ensure indicators like ATR_14 have enough history
    rates = mt5.copy_rates_from_pos(ticker, mt5.TIMEFRAME_D1, 0, 100)

    # Critical: Check if we have at least 15 bars for a 14-period indicator
    if rates is None or len(rates) < 15:
        return pd.DataFrame()

    df = pd.DataFrame(rates)
    df['time'] = pd.to_datetime(df['time'], unit='s')
    df.rename(columns={'time': 'timestamp'}, inplace=True)
    return df


def get_universe():
    try:
        # IMPORT MASTER WATCHLIST
        logger.info(f"✅ Loaded {len(WATCHLIST)} tickers from prop_watchlist.py")
        return WATCHLIST
    except (ImportError, NameError):
        logger.warning("⚠️ prop_watchlist.py not found. Using backup list.")
        return FALLBACK_WATCHLIST