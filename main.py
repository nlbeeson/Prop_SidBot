import asyncio
import logging
from datetime import datetime, timedelta
from logging.handlers import RotatingFileHandler

import MetaTrader5 as mt5
import pytz

from config import *
from fetch_earnings import weekly_maintenance
from kill_switch import close_all_positions
from risk_management import is_drawdown_safe
from mt5_earnings_shield import liquidate_earnings_risk
from mt5_news_filter import is_trading_blocked
from mt5_trailing_stops import apply_trailing_stop
from prop_sid_advisor import run_advisor_scan, send_admin_heartbeat
# Import custom modules (ensure these use the centralized config.py)
from prop_sidbot import run_entry_scan, run_exit_scan

# Logging Configuration
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        RotatingFileHandler("mt5_prop_activity.log", maxBytes=5000000, backupCount=5),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("MT5MasterControl")
logger.propagate = False

TIMEZONE = pytz.timezone('US/Eastern')
TRADING_BLOCKED = False


async def high_frequency_risk_task():
    """Runs every minute: Updates trailing stops and checks news shield with auto-reconnect."""
    global TRADING_BLOCKED
    while True:
        try:
            # 1. Dynamic Reconnection Logic
            # Check if we are actually connected to the broker account
            if mt5.account_info() is None:
                logger.warning("🔄 MT5 Connection lost. Attempting to reconnect...")
                # Attempt to re-initialize using credentials from config
                if mt5.initialize(login=MT5_LOGIN, password=MT5_PASSWORD, server=MT5_SERVER):
                    logger.info("✅ Reconnected to MT5 Broker successfully.")
                else:
                    logger.error(f"❌ Reconnection failed: {mt5.last_error()}")
                    await asyncio.sleep(10)  # Wait a bit before retrying if failed
                    continue

            # 2. Standard Risk Tasks
            # Runs synchronous MT5 code in a separate thread to keep loop responsive
            await asyncio.to_thread(apply_trailing_stop)

            currencies = ['USD', 'EUR', 'GBP', 'JPY', 'CAD', 'AUD', 'NZD', 'CHF']
            # News filter is also a blocking network request, thread it
            blocked, reason = await asyncio.to_thread(is_trading_blocked, currencies)

            if blocked:
                if not TRADING_BLOCKED:
                    logger.warning(f"🚨 NEWS BLOCK ACTIVE: {reason}")
                TRADING_BLOCKED = True
            else:
                TRADING_BLOCKED = False

        except Exception as e:
            logger.error(f"❌ Error in Risk Task: {e}")

        await asyncio.sleep(60)


async def market_monitor_task():
    """Runs every 5 minutes: Checks RSI exits and entry setups if not blocked."""
    while True:
        try:
            # 1. HARD KILL SWITCH: Check for catastrophic drawdown
            # Using 4.7% limit to stay under the 5% firm rule
            if not is_drawdown_safe(limit=0.047):
                logger.critical("🚨 CRITICAL DRAWDOWN REACHED: ACTIVATING EMERGENCY KILL SWITCH")
                await asyncio.to_thread(close_all_positions)
                # Note: Bot continues to loop but entries are blocked by is_drawdown_safe()

            # 2. Standard Maintenance
            await asyncio.to_thread(run_exit_scan)

            if not TRADING_BLOCKED:
                await asyncio.to_thread(run_entry_scan)
            else:
                logger.info("⏸️ Entry scan skipped: News Block Active.")

        except Exception as e:
            # Catch all exceptions to prevent the background task from dying
            logger.error(f"❌ Error in Monitor Task: {e}", exc_info=True)
            # Optional: Add a small sleep here if the error might be persistent (like no internet)
            await asyncio.sleep(10)

        # Always wait for the interval before the next iteration
        await asyncio.sleep(EXIT_CHECK_INTERVAL)


async def schedule_task(func, target_time_str, task_name, *args):
    """Generic scheduler that runs synchronous tasks in a worker thread."""
    while True:
        now = datetime.now(TIMEZONE)
        hour, minute = map(int, target_time_str.split(":"))
        target = now.replace(hour=hour, minute=minute, second=0, microsecond=0)

        if now >= target:
            target += timedelta(days=1)

        wait_seconds = (target - now).total_seconds()
        logger.info(f"🕒 {task_name} scheduled for {target.strftime('%H:%M')} EST.")
        await asyncio.sleep(wait_seconds)

        try:
            # Run the task in a thread to keep the main loop alive
            await asyncio.to_thread(func, *args)
        except Exception as e:
            logger.error(f"❌ Error in {task_name}: {e}")
        await asyncio.sleep(60)


async def schedule_weekly_task(func, target_day, target_time_str, task_name):
    """Calculates the next weekly occurrence and waits to execute."""
    days_map = {"Monday": 0, "Tuesday": 1, "Wednesday": 2, "Thursday": 3, "Friday": 4, "Saturday": 5, "Sunday": 6}
    while True:
        now = datetime.now(TIMEZONE)
        target_day_num = days_map[target_day]
        hour, minute = map(int, target_time_str.split(":"))

        target = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
        # Shift to the correct day of the week
        days_ahead = target_day_num - now.weekday()
        if days_ahead < 0 or (days_ahead == 0 and now >= target):
            days_ahead += 7
        target += timedelta(days=days_ahead)

        wait_seconds = (target - now).total_seconds()
        logger.info(f"📅 {task_name} scheduled for {target.strftime('%A, %b %d @ %H:%M')} EST.")
        await asyncio.sleep(wait_seconds)

        try:
            await asyncio.to_thread(func)
        except Exception as e:
            logger.error(f"❌ Error in {task_name}: {e}")
        await asyncio.sleep(60)


async def main():
    # Use the portable path from your config
    if not mt5.initialize(path=MT5_PATH, portable=True, login=MT5_LOGIN, password=MT5_PASSWORD, server=MT5_SERVER):
        logger.error(f"❌ MT5 Initialization Failed: {mt5.last_error()}")
        return

    # --- NEW: ALGO TRADING SAFETY CHECKS ---
    terminal_info = mt5.terminal_info()
    account_info = mt5.account_info()

    if not terminal_info.trade_allowed:
        logger.critical("⚠️ ALGO TRADING IS DISABLED: Check MT5 Options > Expert Advisors.")
        return

    if not account_info.trade_allowed:
        logger.critical("❌ ACCOUNT TRADING DISABLED: Check 5ers dashboard for violations or maintenance.")
        return

    logger.info("💎 MT5 PROP MASTER CONTROL ONLINE (Algo Trading Enabled)")

    # Group all tasks to run concurrently
    await asyncio.gather(
        high_frequency_risk_task(),
        market_monitor_task(),
        schedule_task(liquidate_earnings_risk, "15:45", "Earnings Shield"),
        schedule_task(send_admin_heartbeat, "09:45", "Admin Heartbeat"),
        schedule_task(run_advisor_scan, "15:00", "Daily Advisor"),
        schedule_weekly_task(weekly_maintenance, "Monday", "00:00", "Weekly Maintenance")
    )


if __name__ == "__main__":
    asyncio.run(main())
