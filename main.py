import asyncio
import logging
from datetime import datetime, timedelta
from typing import List

# ------------------------
# Logging Setup (Windows-safe)
# ------------------------
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger(__name__)

# ------------------------
# Data Provider (ASCII-safe)
# ------------------------
try:
    from prop_watchlist import WATCHLIST
except ImportError:
    WATCHLIST = []


def get_universe() -> List[str]:
    """Return the list of tickers to scan."""
    try:
        tickers = WATCHLIST
        logger.info(f"[INFO] Loaded {len(tickers)} tickers from prop_watchlist.py")
        return tickers
    except Exception as e:
        logger.error(f"[ERROR] Failed to load tickers: {e}")
        return []


def get_account_info() -> dict:
    """Retrieve account info for drawdown checks or position sizing."""
    try:
        # Placeholder for your broker/MT5 API
        account_info = {"balance": 100000, "equity": 100000, "margin": 0}
        return account_info
    except Exception as e:
        logger.error(f"[ERROR] Could not retrieve account info: {e}")
        return {}


# ------------------------
# Strategy Logic
# ------------------------
def check_drawdown_limit() -> bool:
    """Return True if daily drawdown limit reached."""
    try:
        account = get_account_info()
        if not account:
            return True  # fail-safe abort

        daily_drawdown_limit = 0.02
        balance = account.get("balance", 0)
        equity = account.get("equity", 0)
        if balance <= 0:
            return True

        drawdown = (balance - equity) / balance
        if drawdown >= daily_drawdown_limit:
            logger.info("[INFO] Entry scan aborted: Daily drawdown limit reached.")
            return True
        return False
    except Exception as e:
        logger.error(f"[ERROR] Drawdown check failed: {e}")
        return True


async def run_entry_scan():
    """Run the main entry scan logic."""
    if check_drawdown_limit():
        return

    try:
        tickers = await asyncio.to_thread(get_universe)
        if not tickers:
            logger.error("[ERROR] No tickers loaded; skipping entry scan.")
            return

        for ticker in tickers:
            # Replace with your actual trading logic
            logger.info(f"[SCAN] Scanned {ticker} for entry conditions.")

    except Exception as e:
        logger.error(f"[ERROR] Exception during entry scan: {e}")


async def run_weekly_maintenance():
    """Run weekly maintenance tasks."""
    try:
        tickers = await asyncio.to_thread(get_universe)
        logger.info(f"[MAINTENANCE] Weekly maintenance completed for {len(tickers)} tickers.")
    except Exception as e:
        logger.error(f"[ERROR] Weekly maintenance failed: {e}")


# ------------------------
# Scheduler Functions
# ------------------------
async def periodic_entry_scan(interval_minutes: int = 15):
    """Run entry scan periodically."""
    while True:
        await run_entry_scan()
        await asyncio.sleep(interval_minutes * 60)


async def weekly_maintenance_scheduler(day_of_week: int = 0, hour: int = 0, minute: int = 0):
    """Run weekly maintenance at a specific time (0=Monday)."""
    while True:
        now = datetime.now()
        target = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
        # calculate next occurrence
        days_ahead = (day_of_week - now.weekday() + 7) % 7
        if days_ahead == 0 and target < now:
            days_ahead = 7
        target += timedelta(days=days_ahead)
        wait_seconds = (target - now).total_seconds()
        await asyncio.sleep(wait_seconds)
        await run_weekly_maintenance()


# ------------------------
# Main Entry Point
# ------------------------
async def main():
    logger.info("[INFO] PROP_SIDBOT STARTING")

    # Launch periodic tasks
    scan_task = asyncio.create_task(periodic_entry_scan(interval_minutes=15))
    weekly_task = asyncio.create_task(weekly_maintenance_scheduler(day_of_week=0, hour=0, minute=0))

    await asyncio.gather(scan_task, weekly_task)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("[INFO] PROP_SIDBOT STOPPED BY USER")
    except Exception as e:
        logger.error(f"[ERROR] Fatal exception: {e}")
