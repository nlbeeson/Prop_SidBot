import asyncio
from datetime import datetime, timedelta
from logging.handlers import RotatingFileHandler
import logging
import os
import sys
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
from strategies import run_entry_scan, run_exit_scan

# -------------------------------
# Logging Setup
# -------------------------------

# Ensure log directory exists
LOG_DIR = os.path.join(os.path.dirname(__file__), "logs")
os.makedirs(LOG_DIR, exist_ok=True)

LOG_FILE_PATH = os.path.join(LOG_DIR, "bot_activity.log")

# Create a logger for the whole app
logger = logging.getLogger("MT5MasterControl")
logger.setLevel(logging.INFO)

# File handler
file_handler = RotatingFileHandler(LOG_FILE_PATH, maxBytes=5_000_000, backupCount=5)
file_handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s: %(message)s", datefmt="%Y-%m-%d %H:%M:%S"))

# Stream handler (console)
stream_handler = logging.StreamHandler()
stream_handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s: %(message)s", datefmt="%Y-%m-%d %H:%M:%S"))

logger.addHandler(file_handler)
logger.addHandler(stream_handler)
logger.propagate = False

# Log startup
logger.info("=== STARTING PROP_SIDBOT ===")
logger.info(f"Python version: {sys.version}")

# -------------------------------
# Global Exception Hook
# -------------------------------
def log_uncaught_exceptions(exc_type, exc_value, exc_traceback):
    if issubclass(exc_type, KeyboardInterrupt):
        sys.__excepthook__(exc_type, exc_value, exc_traceback)
        return
    logger.critical("UNHANDLED EXCEPTION", exc_info=(exc_type, exc_value, exc_traceback))

sys.excepthook = log_uncaught_exceptions
logger.info("=== Logging setup complete ===")

# -------------------------------
# Timezone & Trading Flags
# -------------------------------
TIMEZONE = pytz.timezone('US/Eastern')
TRADING_BLOCKED = False

# -------------------------------
# Async Task Wrappers
# -------------------------------
async def high_frequency_risk_task():
    global TRADING_BLOCKED
    while True:
        try:
            if mt5.account_info() is None:
                logger.warning("🔄 MT5 Connection lost. Attempting to reconnect...")
                if mt5.initialize(login=MT5_LOGIN, password=MT5_PASSWORD, server=MT5_SERVER):
                    logger.info("✅ Reconnected to MT5 Broker successfully.")
                else:
                    logger.error(f"❌ Reconnection failed: {mt5.last_error()}")
                    await asyncio.sleep(10)
                    continue
            
            await asyncio.to_thread(apply_trailing_stop)
            
            currencies = ['USD','EUR','GBP','JPY','CAD','AUD','NZD','CHF']
            blocked, reason = await asyncio.to_thread(is_trading_blocked, currencies)
            
            if blocked:
                if not TRADING_BLOCKED:
                    logger.warning(f"🚨 NEWS BLOCK ACTIVE: {reason}")
                TRADING_BLOCKED = True
            else:
                TRADING_BLOCKED = False
                
        except Exception as e:
            logger.error(f"❌ Error in Risk Task: {e}", exc_info=True)
        await asyncio.sleep(60)

async def market_monitor_task():
    while True:
        try:
            if not is_drawdown_safe(limit=MAX_DAILY_DRAWDOWN_LIMIT):
                logger.critical("🚨 CRITICAL DRAWDOWN REACHED: ACTIVATING EMERGENCY KILL SWITCH")
                await asyncio.to_thread(close_all_positions)
            
            await asyncio.to_thread(run_exit_scan)
            
            if not TRADING_BLOCKED:
                await asyncio.to_thread(run_entry_scan)
            else:
                logger.info("⏸️ Entry scan skipped: News Block Active.")
                
        except Exception as e:
            logger.error(f"❌ Error in Monitor Task: {e}", exc_info=True)
            await asyncio.sleep(10)
        await asyncio.sleep(EXIT_CHECK_INTERVAL)

async def schedule_task(func, target_time_str, task_name, *args):
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
            await asyncio.to_thread(func, *args)
        except Exception as e:
            logger.error(f"❌ Error in {task_name}: {e}")
            
        await asyncio.sleep(60)

async def schedule_weekly_task(func, target_day, target_time_str, task_name):
    days_map = {"Monday":0,"Tuesday":1,"Wednesday":2,"Thursday":3,"Friday":4,"Saturday":5,"Sunday":6}
    while True:
        now = datetime.now(TIMEZONE)
        target_day_num = days_map[target_day]
        hour, minute = map(int, target_time_str.split(":"))
        
        target = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
        days_ahead = target_day_num - now.weekday()
        if days_ahead < 0 or (days_ahead==0 and now>=target):
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

# -------------------------------
# Main Entry
# -------------------------------
async def main():
    try:
        # Explicitly setting portable=True matches your shortcut flag
        if not mt5.initialize(path=MT5_PATH, portable=True, login=MT5_LOGIN, password=MT5_PASSWORD,
                                server=MT5_SERVER):
            logger.error(f"MT5 initialization FAILED, error: {mt5.last_error()}")
            return
        logger.info("MT5 attached successfully in portable mode")
    except Exception as e:
        logger.exception(f"Exception during MT5 initialization: {e}")
        return

    terminal_info = mt5.terminal_info()
    account_info = mt5.account_info()

    if not terminal_info.trade_allowed:
        logger.critical("⚠️ ALGO TRADING IS DISABLED: Check MT5 Options > Expert Advisors.")
        return

    if not account_info.trade_allowed:
        logger.critical("❌ ACCOUNT TRADING DISABLED: Check 5ers dashboard for violations or maintenance.")
        return

    logger.info("💎 MT5 PROP MASTER CONTROL ONLINE (Algo Trading Enabled)")

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
