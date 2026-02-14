try:
    import pandas_ta as ta
except ImportError:
    # Handle the case where pandas_ta is not installed or accessible
    pass
import MetaTrader5 as mt5
import pandas as pd
import logging
from datetime import datetime, time

from config import *
from risk_management import is_drawdown_safe, is_earnings_safe, get_current_currency_exposure, is_instrument_enabled
from mt5_news_filter import is_trading_blocked
from utils import get_symbol_category
from data_provider import get_data, get_universe
from trade_executor import execute_mt5_trade, close_position_and_orders

logger = logging.getLogger("MT5MasterControl")


def calculate_dynamic_stop(df, ticker, order_type):
    """Calculates SL using unified VOLATILITY_MULT from config."""
    df.ta.atr(length=14, append=True)
    atr_cols = [col for col in df.columns if 'ATR' in col.upper()]
    if not atr_cols: return None

    atr = df[atr_cols[-1]].iloc[-1]
    curr_price = df['close'].iloc[-1]

    category = get_symbol_category(ticker)
    multiplier = VOLATILITY_MULT.get(category, 2.0)
    dist = atr * multiplier

    if order_type == mt5.ORDER_TYPE_BUY:
        return min(curr_price - dist, df['low'].tail(3).min())
    else:
        return max(curr_price + dist, df['high'].tail(3).max())


def run_exit_scan():
    """Checks positions and closes only if RSI 50 is hit AND momentum stalls."""
    try:
        positions = mt5.positions_get()
        if not positions: return

        for pos in positions:
            if pos.magic != MAGIC_NUMBER: continue  # Use constant from config

            rates = mt5.copy_rates_from_pos(pos.symbol, mt5.TIMEFRAME_D1, 0, 50)
            if rates is None or len(rates) < 2: continue

            df = pd.DataFrame(rates)
            df.ta.rsi(length=14, append=True)

            curr_rsi = df['RSI_14'].iloc[-1]
            prev_rsi = df['RSI_14'].iloc[-2]

            # LONG EXIT: RSI hit 50, but only exit if RSI is no longer rising
            if pos.type == mt5.POSITION_TYPE_BUY:
                if curr_rsi >= 50 and curr_rsi <= prev_rsi:
                    logger.info(f"💰 EXIT LONG: {pos.symbol} RSI {curr_rsi:.1f} (Momentum Stalled)")
                    close_position_and_orders(pos.symbol)

            # SHORT EXIT: RSI hit 50, but only exit if RSI is no longer falling
            elif pos.type == mt5.POSITION_TYPE_SELL:
                if curr_rsi <= 50 and curr_rsi >= prev_rsi:
                    logger.info(f"💰 EXIT SHORT: {pos.symbol} RSI {curr_rsi:.1f} (Momentum Stalled)")
                    close_position_and_orders(pos.symbol)
    except Exception as e:
        logger.error(f"Error in exit scan: {e}")


def run_entry_scan():
    # 1. Existing Drawdown Check
    if not is_drawdown_safe():
        logger.info("⏸️ Entry scan aborted: Daily drawdown limit reached.")
        return

    # 2. NEW: Market Rollover / Maintenance Block (4:45 PM - 5:15 PM EST/Server Time)
    # Note: Adjust the timezone based on whether your server/MT5 uses EST or UTC
    now_time = datetime.now().time()
    block_start = time(16, 50)  # 16:45 = 4:45 PM
    block_end = time(17, 10)  # 17:15 = 5:15 PM

    if block_start <= now_time <= block_end:
        logger.info(f"⏸️ Entry scan blocked: Market rollover period ({now_time}).")
        return

    """Scans universe and enters positions using MT5."""
    run_exit_scan()

    positions = mt5.positions_get()
    existing_symbols = {p.symbol for p in positions} if positions else set()

    slots_available = MAX_POSITIONS - len(existing_symbols)
    if slots_available <= 0:
        return

    universe = get_universe()
    candidates = []

    for ticker in universe:
        # Check if this instrument type is currently enabled
        if not is_instrument_enabled(ticker):
            continue

        # --- News Filter Integration ---
        category = get_symbol_category(ticker)
        if category == "FOREX":
            # Extract currency components (e.g., 'EURUSD' -> ['EUR', 'USD'])
            currencies = [ticker[:3], ticker[3:]]
            blocked, reason = is_trading_blocked(currencies)
            if blocked:
                logger.warning(f"🛑 NEWS BLOCK: Skipping {ticker} due to {reason}")
                continue

        if ticker in existing_symbols: continue

        df = get_data(ticker)
        if df.empty or len(df) < 50: continue

        # Technical Analysis (RSI, MACD, Weekly RSI)
        df.ta.rsi(length=14, append=True)
        df.ta.macd(fast=12, slow=26, signal=9, append=True)
        macd_col = df.columns[-3]

        weekly = df.resample('W-FRI', on='timestamp').agg({'close': 'last'}).dropna()
        if len(weekly) < 2: continue
        weekly.ta.rsi(length=14, append=True)

        curr, prev = df.iloc[-1], df.iloc[-2]
        wk_rising = weekly.iloc[-1]['RSI_14'] > weekly.iloc[-2]['RSI_14']
        wk_falling = weekly.iloc[-1]['RSI_14'] < weekly.iloc[-2]['RSI_14']
        rsi_history = df['RSI_14'].tail(SIGNAL_DAYS)

        # LONG Logic
        if (curr['RSI_14'] <= 45 and curr['RSI_14'] > prev['RSI_14'] and
                curr[macd_col] > prev[macd_col] and wk_rising and (rsi_history < 30).any()):

            # Only run earnings check for stocks
            category = get_symbol_category(ticker)
            earnings_ok = is_earnings_safe(ticker) if category == "STOCKS" else True

            if earnings_ok:
                # Use the dynamic stop loss
                stop_price = calculate_dynamic_stop(df, ticker, mt5.ORDER_TYPE_BUY)

                candidates.append({
                    'ticker': ticker, 'type': mt5.ORDER_TYPE_BUY,
                    'score': curr['RSI_14'], 'price': curr['close'], 'stop_price': stop_price,
                    'is_long': True
                })

        # SHORT Logic
        elif ALLOW_SHORTS and (curr['RSI_14'] >= 55 and curr['RSI_14'] < prev['RSI_14'] and
                               curr[macd_col] < prev[macd_col] and wk_falling and (rsi_history > 70).any()):

            # Only run earnings check for stocks
            category = get_symbol_category(ticker)
            earnings_ok = is_earnings_safe(ticker) if category == "STOCKS" else True

            if earnings_ok:
                # Use the dynamic stop loss
                stop_price = calculate_dynamic_stop(df, ticker, mt5.ORDER_TYPE_SELL)

                candidates.append({
                    'ticker': ticker, 'type': mt5.ORDER_TYPE_SELL,
                    'score': 100 - curr['RSI_14'], 'price': curr['close'], 'stop_price': stop_price,
                    'is_long': False
                })

    # --- SORTING LOGIC ---
    # Sort by score: Best Longs (lowest RSI) and Best Shorts (highest RSI) first
    candidates.sort(key=lambda x: x['score'])
    top_picks = candidates[:slots_available]

    for pick in top_picks:
        ticker = pick['ticker']
        category = get_symbol_category(ticker)

        # Apply risk correlation logic only to Forex pairs
        if category == "FOREX":
            exposure = get_current_currency_exposure(ticker)

            if exposure >= MAX_CURRENCY_EXPOSURE:
                if CORRELATION_MODE == 'BLOCK':
                    logger.warning(f"🚫 CORRELATION BLOCK: {ticker} skipped. Max exposure reached.")
                    continue
                elif CORRELATION_MODE == 'REDUCE':
                    logger.info(f"⚠️ CORRELATION RISK: Reducing size for {ticker}.")
                    pick['risk_modifier'] = CORRELATION_RISK_MODIFIER
            else:
                pick['risk_modifier'] = 1.0
        else:
            pick['risk_modifier'] = 1.0

        if TRADE_ALLOWED:
            execute_mt5_trade(pick)
        else:
            # Still logs the "would-be" trade for your review
            logger.info(f"🔍 SIGNAL ONLY: {pick['ticker']} setup identified (RSI: {pick['score']:.1f})")
