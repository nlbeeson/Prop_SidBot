import json
import logging
from datetime import datetime
from pathlib import Path

import MetaTrader5 as mt5

from config import MAGIC_NUMBER

logger = logging.getLogger("MT5Master")


def liquidate_earnings_risk():
    """Identifies and closes stock positions with imminent earnings reports."""
    # Define cache path (aligned with fetch_earnings.py structure)
    base_path = Path(__file__).parent.resolve()
    cache_path = base_path / 'earnings_cache.json'

    if not cache_path.exists():
        logger.warning("⚠️ Earnings cache not found. Skipping liquidation check.")
        return

    try:
        with open(cache_path, 'r') as f:
            earnings_data = json.load(f)

        positions = mt5.positions_get()
        if not positions:
            return

        for pos in positions:
            symbol = pos.symbol

            # 1. Determine if the symbol is a stock
            symbol_info = mt5.symbol_info(symbol)
            path = symbol_info.path.upper() if symbol_info else ""

            if "STOCK" in path or "EQUITY" in path:
                if symbol in earnings_data:
                    report_date = datetime.strptime(earnings_data[symbol], '%Y-%m-%d').date()
                    today = datetime.now().date()

                    # 2. Check if earnings are today or tomorrow
                    # We close if days_until is 0 (today) or 1 (tomorrow morning)
                    days_until = (report_date - today).days

                    if 0 <= days_until <= 1:
                        logger.info(f"🛑 EARNINGS RISK: Closing {symbol}. Report on {report_date}")
                        close_mt5_position(pos)
    except Exception as e:
        logger.error(f"❌ Error during earnings liquidation: {e}")


def close_mt5_position(position):
    """Executes the actual closure of an MT5 position."""
    tick = mt5.symbol_info_tick(position.symbol)
    order_type = mt5.ORDER_TYPE_SELL if position.type == mt5.POSITION_TYPE_BUY else mt5.ORDER_TYPE_BUY
    price = tick.bid if order_type == mt5.ORDER_TYPE_SELL else tick.ask

    request = {
        "action": mt5.TRADE_ACTION_DEAL,
        "symbol": position.symbol,
        "volume": position.volume,
        "type": order_type,
        "position": position.ticket,
        "price": price,
        "deviation": 20,
        "magic": MAGIC_NUMBER,
        "comment": "Earnings Shield Exit",
        "type_time": mt5.ORDER_TIME_GTC,
        "type_filling": mt5.ORDER_FILLING_IOC,
    }
    result = mt5.order_send(request)
    if result.retcode != mt5.TRADE_RETCODE_DONE:
        logger.error(f"❌ Failed to close {position.symbol}: {result.comment}")
