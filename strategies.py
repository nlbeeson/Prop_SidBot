import logging
from data_provider import get_universe, get_account_info

logger = logging.getLogger(__name__)

# ------------------------
# Strategy Functions
# ------------------------
def check_drawdown_limit() -> bool:
    """
    Return True if daily drawdown limit reached.
    """
    try:
        account = get_account_info()
        if not account:
            return True  # abort if account info not available

        # Example: 2% daily drawdown limit
        daily_drawdown_limit = 0.02
        equity = account.get("equity", 0)
        balance = account.get("balance", 0)
        if balance <= 0:
            return True  # prevent division by zero

        drawdown = (balance - equity) / balance
        if drawdown >= daily_drawdown_limit:
            logger.info("[INFO] Entry scan aborted: Daily drawdown limit reached.")
            return True
        return False
    except Exception as e:
        logger.error(f"[ERROR] Drawdown check failed: {e}")
        return True  # fail-safe abort

def run_entry_scan():
    """
    Run the main entry scan logic.
    """
    if check_drawdown_limit():
        return  # stop scanning if drawdown limit reached

    try:
        tickers = get_universe()
        if not tickers:
            logger.error("[ERROR] No tickers loaded; skipping entry scan.")
            return

        # TODO: Replace with your actual entry logic
        for ticker in tickers:
            # Placeholder for actual scanning logic
            logger.info(f"[SCAN] Scanned {ticker} for entry conditions.")

    except Exception as e:
        logger.error(f"[ERROR] Exception during entry scan: {e}")

def run_weekly_maintenance():
    """
    Run weekly maintenance tasks.
    """
    try:
        # Example maintenance: log the number of tickers
        tickers = get_universe()
        logger.info(f"[MAINTENANCE] Weekly maintenance completed for {len(tickers)} tickers.")
    except Exception as e:
        logger.error(f"[ERROR] Weekly maintenance failed: {e}")
