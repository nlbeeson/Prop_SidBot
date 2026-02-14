import asyncio
import logging
import subprocess
import MetaTrader5 as mt5
from strategies import run_entry_scan  # <-- your real scan logic

# --- Logging Setup ---
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.FileHandler("bot.log", encoding="utf-8"), logging.StreamHandler()]
)
logger = logging.getLogger(__name__)

# --- MT5 Terminal Path ---
MT5_PATH = r"C:\Trading\TradingTerminals\MT5_1\terminal64.exe"

# --- Launch MT5 in portable mode ---
def launch_mt5_portable():
    if not os.path.exists(MT5_PATH):
        logger.error(f"MT5 executable not found at {MT5_PATH}")
        return False
    try:
        subprocess.Popen([MT5_PATH, "/portable"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        logger.info("✅ MT5 terminal launched in portable mode")
        return True
    except Exception as e:
        logger.exception(f"Failed to launch MT5: {e}")
        return False

# --- Periodic Entry Scan ---
async def periodic_entry_scan():
    while True:
        try:
            await run_entry_scan()  # <-- your real logic from strategies.py
        except Exception as e:
            logger.exception(f"Error during entry scan: {e}")
        await asyncio.sleep(60)  # adjust interval as needed

# --- Initialize MT5 API ---
async def initialize_mt5():
    if not mt5.initialize(path=MT5_PATH):
        err = mt5.last_error()
        logger.error(f"MT5 failed to initialize: {err}")
        return False
    logger.info("✅ MT5 API initialized successfully")
    return True

# --- Main Bot ---
async def main():
    # Launch MT5 first
    if not launch_mt5_portable():
        logger.error("Exiting bot because MT5 failed to launch.")
        return

    # Give MT5 some time to start
    await asyncio.sleep(5)

    # Initialize MT5 API
    if not await initialize_mt5():
        logger.error("Exiting bot because MT5 API failed to initialize.")
        return

    # Start periodic scanning
    await periodic_entry_scan()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Bot stopped manually.")
    finally:
        mt5.shutdown()
        logger.info("MT5 connection closed.")
