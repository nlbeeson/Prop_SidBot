import asyncio
import logging
from datetime import datetime, timedelta
from strategies import run_entry_scan, run_weekly_maintenance

# ------------------------
# Logging Setup
# ------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
    handlers=[logging.FileHandler("bot.log", encoding="utf-8"), logging.StreamHandler()]
)

logger = logging.getLogger(__name__)

# ------------------------
# Helper Logging Functions
# ------------------------
def log_info(message: str):
    """ASCII-safe info logging."""
    logger.info(message)

def log_error(message: str):
    """ASCII-safe error logging."""
    logger.error(message)

# ------------------------
# Scheduled Tasks
# ------------------------
async def periodic_entry_scan(interval_minutes: int = 5):
    """Run entry scan every X minutes."""
    while True:
        try:
            await asyncio.to_thread(run_entry_scan)
        except Exception as e:
            log_error(f"Error during entry scan: {e}")
        await asyncio.sleep(interval_minutes * 60)

async def weekly_maintenance_task(day_of_week: int = 0, hour: int = 0, minute: int = 0):
    """
    Run weekly maintenance.
    day_of_week: 0=Monday ... 6=Sunday
    """
    while True:
        now = datetime.now()
        next_run = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
        days_ahead = (day_of_week - now.weekday()) % 7
        if days_ahead == 0 and next_run < now:
            days_ahead = 7
        next_run += timedelta(days=days_ahead)
        sleep_seconds = (next_run - now).total_seconds()
        await asyncio.sleep(sleep_seconds)

        try:
            await asyncio.to_thread(run_weekly_maintenance)
        except Exception as e:
            log_error(f"Error during weekly maintenance: {e}")

# ------------------------
# Main Function
# ------------------------
async def main():
    log_info("PROP_SIDBOT STARTING (Windows-safe logging enabled)")

    # Schedule tasks
    entry_scan_task = asyncio.create_task(periodic_entry_scan(interval_minutes=5))
    weekly_task = asyncio.create_task(weekly_maintenance_task(day_of_week=0, hour=0, minute=0))

    # Keep the bot running
    await asyncio.gather(entry_scan_task, weekly_task)

# ------------------------
# Run Bot
# ------------------------
if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        log_info("PROP_SIDBOT SHUTDOWN REQUESTED")
    except Exception as e:
        log_error(f"Unhandled exception in main: {e}")
