import logging

import MetaTrader5 as mt5
import pandas as pd
import pandas_ta_classic

from config import *
from utils import get_symbol_category

logger = logging.getLogger("MT5Master")


def apply_trailing_stop():
    """Updates SL for all positions based on ATR to lock in gains."""
    positions = mt5.positions_get()
    if not positions:
        return

    for pos in positions:
        if pos.magic != MAGIC_NUMBER: continue  # Skip manual trades
        symbol = pos.symbol
        # Fetch fresh data for ATR calculation
        rates = mt5.copy_rates_from_pos(symbol, mt5.TIMEFRAME_D1, 0, 50)
        if rates is None or len(rates) < 20: continue

        df = pd.DataFrame(rates)
        df.ta.atr(length=14, append=True)
        current_atr = df.iloc[-1][df.columns[df.columns.str.contains('ATR')][-1]]

        # Get category to apply correct multiplier
        category = get_symbol_category(symbol)  # Helper from prop_sidbot
        trail_dist = current_atr * VOLATILITY_MULT.get(category, 2.0)

        tick = mt5.symbol_info_tick(symbol)
        if tick is None: continue

        new_sl = 0.0
        # LONG: SL moves UP as Bid price rises
        if pos.type == mt5.POSITION_TYPE_BUY:
            potential_sl = tick.bid - trail_dist
            if potential_sl > pos.sl + (current_atr * 0.1):  # Only move if change > 10% of ATR
                new_sl = potential_sl

        # SHORT: SL moves DOWN as Ask price falls
        elif pos.type == mt5.POSITION_TYPE_SELL:
            potential_sl = tick.ask + trail_dist
            if pos.sl == 0 or potential_sl < pos.sl - (current_atr * 0.1):
                new_sl = potential_sl

        if new_sl > 0:
            request = {
                "action": mt5.TRADE_ACTION_SLTP,
                "symbol": symbol,
                "position": pos.ticket,
                "sl": float(round(new_sl, 5)),
                "tp": pos.tp,
                "type_time": mt5.ORDER_TIME_GTC,
                "type_filling": mt5.ORDER_FILLING_IOC,
            }
            result = mt5.order_send(request)
            if result.retcode == mt5.TRADE_RETCODE_DONE:
                logger.info(f"📈 Trailing SL updated for {symbol}: {new_sl:.5f}")
