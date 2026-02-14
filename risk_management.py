import MetaTrader5 as mt5
import json
import logging
from datetime import datetime, time
from pathlib import Path

from config import *
from utils import get_symbol_category

logger = logging.getLogger("MT5MasterControl")


def is_instrument_enabled(symbol):
    """
    Returns True if the category for the given symbol is enabled in TRADE_SETTINGS.
    """
    category = get_symbol_category(symbol)
    return TRADE_SETTINGS.get(category, False)


def is_market_open(symbol):
    """
    Checks if the market for a specific symbol is currently open for trading.
    """
    info = mt5.symbol_info(symbol)
    if info is None:
        return False

    # Check trade_mode (Disabled, Long Only, Full Access, etc.)
    if info.trade_mode == mt5.SYMBOL_TRADE_MODE_DISABLED:
        return False

    # Check the actual session
    # This checks if the broker is currently accepting orders for this symbol
    if info.trade_mode == mt5.SYMBOL_TRADE_MODE_FULL:
        return True

    return False


def is_earnings_safe(ticker):
    # Standardized to current folder
    cache_path = Path(__file__).parent.resolve() / 'earnings_cache.json'

    if not cache_path.exists():
        logger.warning(f"⚠️ Missing cache at {cache_path}. Blocking {ticker}.")
        return False

    try:
        with open(cache_path, 'r') as f:
            earnings_data = json.load(f)

        if ticker not in earnings_data:
            # If ticker isn't in the calendar, Alpha Vantage doesn't see
            # an event in the 3-month horizon. Usually safe to trade.
            return True

        next_earnings_date = datetime.strptime(earnings_data[ticker], '%Y-%m-%d').date()
        today = datetime.now().date()
        days_until = (next_earnings_date - today).days

        if 0 <= days_until <= 14:
            logger.info(f"[{ticker}] Earnings in {days_until} days ({next_earnings_date}). BLOCKING.")
            return False

        return True

    except Exception as e:
        logger.error(f"[{ticker}] Earnings Check Error: {e}. BLOCKING.")
        return False


def get_current_currency_exposure(new_ticker):
    """Counts how many times base/quote currencies of new_ticker appear in open trades."""
    positions = mt5.positions_get()
    if not positions:
        return 0

    new_currencies = [new_ticker[:3], new_ticker[3:]]
    exposure_count = 0

    for pos in positions:
        # Extract base and quote from open position symbols
        active_currencies = [pos.symbol[:3], pos.symbol[3:]]
        for cur in new_currencies:
            if cur in active_currencies:
                exposure_count += 1

    return exposure_count


def is_drawdown_safe(limit=None):  # Add 'limit=None' to accept the argument from main.py
    """Checks if the current daily drawdown exceeds the allowed limit using MT5 history."""
    try:
        # Use the passed limit (0.047) if available, otherwise fall back to config
        drawdown_limit = limit if limit is not None else MAX_DAILY_DRAWDOWN_PCT

        account = mt5.account_info()
        if account is None:
            logger.error("❌ Could not retrieve account info for drawdown check.")
            return False

        current_equity = account.equity

        # Calculate Start-of-Day Balance
        today_start = datetime.combine(datetime.now().date(), time.min)
        history_deals = mt5.history_deals_get(today_start, datetime.now())

        today_realized_pl = 0
        if history_deals:
            for deal in history_deals:
                today_realized_pl += (deal.profit + deal.commission + deal.fee + deal.swap)

        start_of_day_balance = account.balance - today_realized_pl

        if start_of_day_balance <= 0:
            return True

        # Calculate current drawdown percentage
        current_drawdown = (start_of_day_balance - current_equity) / start_of_day_balance

        # --- KEEP THIS UPDATED BLOCK ---
        # It now compares against the dynamic 'drawdown_limit'
        if current_drawdown >= drawdown_limit:
            logger.warning(
                f"⚠️ DRAWDOWN ALERT: Current loss ({current_drawdown:.2%}) exceeds limit ({drawdown_limit:.2%}).")
            return False

        return True

    except Exception as e:
        logger.error(f"❌ Error checking drawdown: {e}")
        return False