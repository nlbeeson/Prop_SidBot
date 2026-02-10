import argparse
import csv
import json
import logging
import sys
from datetime import datetime
from pathlib import Path

import MetaTrader5 as mt5
import pandas as pd
import pandas_ta_classic

from config import *
from mt5_check_daily_drawdown import is_drawdown_safe
from mt5_news_filter import is_trading_blocked
# Import Watchlist
from prop_watchlist import WATCHLIST

src_folder = Path(__file__).resolve().parent
env_path = src_folder / '.env'

load_dotenv(dotenv_path=env_path)

logger = logging.getLogger("MT5MasterControl")

FALLBACK_WATCHLIST = [
    'GBPNZD', 'GBPJPY', 'EURNZD', 'CHFJPY', 'GBPAUD', 'GBPAUD', 'GBPCAD', 'GBPCHF', 'NZDJPY', 'EURCAD',
    'CADJPY', 'AUDNZD', 'AUDJPY', 'USDCHF', 'NZDCHF', 'EURAUD', 'AUDCAD', 'NZDCAD', 'EURCHF', 'AUDCHF',
    'USDJPY', 'USDCAD', 'NZDUSD', 'GBPUSD', 'EURUSD', 'EURJPY', 'CADCHF', 'AUDUSD',
]


def initialize_mt5():
    """Initializes MT5 using credentials from .env"""
    # Use the logic from your mt5_test.py here
    login = int(os.getenv("MT5_LOGIN"))
    password = os.getenv("MT5_PASSWORD")
    server = os.getenv("MT5_SERVER")

    if not mt5.initialize(login=login, password=password, server=server):
        print(f"Failed to initialize MT5: {mt5.last_error()}")
        sys.exit(1)
    print(f"Connected to MT5: {mt5.account_info().login}")


def mt5_shutdown():
    mt5.shutdown()


def get_universe():
    try:
        # IMPORT MASTER WATCHLIST
        print(f"✅ Loaded {len(WATCHLIST)} tickers from prop_watchlist.py")
        return WATCHLIST
    except (ImportError, NameError):
        print("⚠️ prop_watchlist.py not found. Using backup list.")
        return FALLBACK_WATCHLIST


def get_data(ticker):
    # Fetch 100 bars to ensure indicators like ATR_14 have enough history
    rates = mt5.copy_rates_from_pos(ticker, mt5.TIMEFRAME_D1, 0, 100)

    # Critical: Check if we have at least 15 bars for a 14-period indicator
    if rates is None or len(rates) < 15:
        return pd.DataFrame()

    df = pd.DataFrame(rates)
    df['time'] = pd.to_datetime(df['time'], unit='s')
    df.rename(columns={'time': 'timestamp'}, inplace=True)
    return df


def get_symbol_category(symbol):
    """Identifies category using unified config map and MT5 path."""
    for key, category in CATEGORY_MAP.items():
        if key in symbol:
            return category

    info = mt5.symbol_info(symbol)
    if info:
        path = info.path.upper()
        if "FOREX" in path: return "FOREX"
        if "STOCK" in path or "EQUITY" in path: return "STOCKS"
        if "INDEX" in path or "INDICES" in path: return "INDICES"
    return "FOREX"


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
        print(f"⚠️ Missing cache at {cache_path}. Blocking {ticker}.")
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
            print(f"[{ticker}] Earnings in {days_until} days ({next_earnings_date}). BLOCKING.")
            return False

        return True

    except Exception as e:
        print(f"[{ticker}] Earnings Check Error: {e}. BLOCKING.")
        return False


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


def apply_trailing_stop():
    """Loops through all open positions and updates SL based on ATR volatility."""
    positions = mt5.positions_get()
    if not positions:
        return

    for pos in positions:
        symbol = pos.symbol
        df = get_data(symbol)
        if df.empty or len(df) < 20:
            continue

        # 1. Calculate ATR
        df.ta.atr(length=14, append=True)
        atr_cols = [col for col in df.columns if 'ATR' in col.upper()]

        if not atr_cols:
            print(f"⚠️ ATR calculation failed for {symbol}")
            continue

        current_atr = df[atr_cols[-1]].iloc[-1]
        category = get_symbol_category(symbol)

        trail_dist = current_atr * VOLATILITY_MULT.get(category, 2.0)

        # MOVE THESE INSIDE THE LOOP
        tick = mt5.symbol_info_tick(symbol)
        if tick is None: continue

        current_sl = pos.sl
        new_sl = 0.0

        # 2. Logic for Long Positions
        if pos.type == mt5.POSITION_TYPE_BUY:
            potential_sl = tick.bid - trail_dist
            if potential_sl > current_sl + (current_atr * 0.1):
                new_sl = potential_sl

        # 3. Logic for Short Positions
        elif pos.type == mt5.POSITION_TYPE_SELL:
            potential_sl = tick.ask + trail_dist
            if current_sl == 0 or potential_sl < current_sl - (current_atr * 0.1):
                new_sl = potential_sl

        # 4. Execute the Update
        if new_sl > 0:
            request = {
                "action": mt5.TRADE_ACTION_SLTP,
                "symbol": symbol,
                "position": pos.ticket,
                "sl": float(new_sl),
                "tp": pos.tp,
                "type_time": mt5.ORDER_TIME_GTC,
                "type_filling": mt5.ORDER_FILLING_IOC,
            }
            result = mt5.order_send(request)
            if result.retcode == mt5.TRADE_RETCODE_DONE:
                print(f"📈 Trailing SL updated for {symbol} to {new_sl:.5f}")


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


def log_event(event_data):
    """
    Saves trade attempts and errors to a CSV file in the project root.
    """
    # Resolve the path relative to this script's folder
    base_path = Path(__file__).parent.resolve()
    log_file = base_path / "trade_log.csv"

    file_exists = log_file.exists()

    # Define headers
    headers = [
        "timestamp", "symbol", "action", "status",
        "lots", "price", "sl", "spread_pips", "comment"
    ]

    with open(log_file, "a", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=headers)
        if not file_exists:
            writer.writeheader()

        # Ensure timestamp is included
        event_data["timestamp"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        writer.writerow(event_data)


# --- EXITS ---
def close_position_and_orders(symbol):
    """Closes all positions and cancels pending orders for a symbol."""
    # 1. Cancel Pending Orders
    orders = mt5.orders_get(symbol=symbol)
    if orders:
        for order in orders:
            cancel_req = {
                "action": mt5.TRADE_ACTION_REMOVE,
                "order": order.ticket
            }
            mt5.order_send(cancel_req)

    # 2. Close Active Positions
    positions = mt5.positions_get(symbol=symbol)
    if positions:
        info = mt5.symbol_info(symbol)
        for pos in positions:
            if pos.magic != MAGIC_NUMBER: continue  # Skip manual trades

            info = mt5.symbol_info(symbol)
            if info.filling_mode & 1:
                filling_type = mt5.ORDER_FILLING_FOK
            elif info.filling_mode & 2:
                filling_type = mt5.ORDER_FILLING_IOC
            else:
                filling_type = mt5.ORDER_FILLING_RETURN

            tick = mt5.symbol_info_tick(symbol)
            # 0 is Buy (Long), 1 is Sell (Short)
            order_type = mt5.ORDER_TYPE_SELL if pos.type == mt5.POSITION_TYPE_BUY else mt5.ORDER_TYPE_BUY
            price = tick.bid if order_type == mt5.ORDER_TYPE_SELL else tick.ask

            request = {
                "action": mt5.TRADE_ACTION_DEAL,
                "symbol": symbol,
                "volume": pos.volume,
                "type": order_type,
                "position": pos.ticket,  # MUST link to the original position
                "price": price,
                "deviation": 20,
                "magic": 123456,
                "comment": "Bot Exit",
                "type_time": mt5.ORDER_TIME_GTC,
                "type_filling": filling_type,  # Immediate or Cancel
            }
            mt5.order_send(request)


def run_exit_scan():
    """Checks positions and closes only if RSI 50 is hit AND momentum stalls."""
    positions = mt5.positions_get()
    if not positions: return

    for pos in positions:
        if pos.magic != MAGIC_NUMBER: continue  # Use constant from config

        rates = mt5.copy_rates_from_pos(pos.symbol, mt5.TIMEFRAME_D1, 0, 50)
        if rates is None: continue

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


# --- ENTRIES ---
def run_entry_scan():
    if not is_drawdown_safe():
        print("⏸️ Entry scan aborted: Daily drawdown limit reached.")
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
                print(f"🛑 NEWS BLOCK: Skipping {ticker} due to {reason}")
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
                    'score': curr['RSI_14'], 'price': curr['close'], 'stop_price': stop_price
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
                    'score': 100 - curr['RSI_14'], 'price': curr['close'], 'stop_price': stop_price
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

def execute_mt5_trade(pick):
    symbol = pick['ticker']
    info = mt5.symbol_info(symbol)
    if info is None: return

    # Bitmask check: SYMBOL_FILLING_FOK is 1, SYMBOL_FILLING_IOC is 2
    # In Python MT5, these bitmask constants are often missing, so we use integers:
    # 1 = FOK, 2 = IOC

    if info.filling_mode & 1:  # FOK supported
        filling_type = mt5.ORDER_FILLING_FOK
    elif info.filling_mode & 2:  # IOC supported
        filling_type = mt5.ORDER_FILLING_IOC
    else:
        filling_type = mt5.ORDER_FILLING_RETURN

    # 1. Spread Calculation
    # info.digits handles JPY (3) vs EURUSD (5)
    tick = mt5.symbol_info_tick(symbol)
    pip_unit = 10 ** - (info.digits - 1)
    current_spread = (tick.ask - tick.bid) / pip_unit

    if current_spread > MAX_SPREAD_PIPS:
        print(f"⚠️ Spread too high for {symbol}: {current_spread:.1f}")
        log_event({
            "symbol": symbol, "action": "SKIP", "status": "HIGH_SPREAD",
            "spread_pips": round(current_spread, 2), "comment": "Spread Filter"
        })
        return

    # Dynamic Risk Calculation
    # 1. Apply the dynamic risk modifier (from the 'pick' dictionary)
    # If no modifier is provided, it defaults to 1.0 (100% risk)
    effective_risk_pct = RISK_PER_TRADE_PCT * pick.get('risk_modifier', 1.0)

    # 2. Risk-Based Lot Calculation
    # Calculate cash risk based on the modified percentage
    equity = mt5.account_info().equity
    risk_cash = equity * effective_risk_pct

    # 3. Final Lot Sizing
    price_dist = abs(pick['price'] - pick['stop_price'])
    if price_dist == 0: return

    # Scale by contract size: FX (100k), Gold (100), Indices (1)
    raw_lots = risk_cash / (price_dist * info.trade_contract_size)

    # Step-size normalization
    lot = round(raw_lots / info.volume_step) * info.volume_step
    lot = max(info.volume_min, min(info.volume_max, lot))

    # 3. Send Order
    order_type = pick['type']
    price = tick.ask if order_type == mt5.ORDER_TYPE_BUY else tick.bid

    request = {
        "action": mt5.TRADE_ACTION_DEAL,
        "symbol": symbol,
        "volume": round(lot, 2),
        "type": order_type,
        "price": price,
        "sl": float(pick['stop_price']),
        "magic": MAGIC_NUMBER,
        "comment": "Sid Bot Entry",
        "type_time": mt5.ORDER_TIME_GTC,
        "type_filling": filling_type,
    }

    result = mt5.order_send(request)

    # 4. Log Result
    status = "SUCCESS" if result.retcode == mt5.TRADE_RETCODE_DONE else f"FAIL_{result.retcode}"
    log_event({
        "symbol": symbol, "action": "BUY" if order_type == 0 else "SELL",
        "status": status, "lots": round(lot, 2), "price": price,
        "sl": pick['stop_price'], "spread_pips": round(current_spread, 2),
        "comment": result.comment if result else "No Result"
    })

    if result.retcode == mt5.TRADE_RETCODE_DONE:
        print(f"✅ Trade executed: {symbol} at {price}")
    else:
        print(f"❌ Trade failed: {result.comment}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='MT5 Forex Sid Method Trading Bot')
    parser.add_argument('--mode', type=str, required=True, choices=['entry', 'exit', 'trail'],
                        help='entry: daily scan, exit: RSI targets, trail: move stop losses')

    # Optional switches to disable categories via command line
    parser.add_argument('--no-stocks', action='store_true', help='Disable Stock trading')
    parser.add_argument('--no-crypto', action='store_true', help='Disable Crypto trading')
    parser.add_argument('--no-forex', action='store_true', help='Disable Forex trading')

    args = parser.parse_args()

    # Apply CLI overrides to TRADE_SETTINGS
    if args.no_stocks: TRADE_SETTINGS["STOCKS"] = False
    if args.no_crypto: TRADE_SETTINGS["CRYPTO"] = False
    if args.no_forex:  TRADE_SETTINGS["FOREX"] = False

    try:
        initialize_mt5()

        # --- EXECUTION MODES ---
        if args.mode == 'trail':
            # Fast check: Move stop losses based on ATR volatility
            print(f"[{datetime.now().strftime('%H:%M:%S')}] Running Trailing Stop Update...")
            apply_trailing_stop()

        elif args.mode == 'exit':
            # Hourly check: Close positions if RSI crosses 50
            print(f"[{datetime.now().strftime('%H:%M:%S')}] Running RSI Exit Scan...")
            run_exit_scan()

        elif args.mode == 'entry':
            # Daily check: Find new trade setups
            run_entry_scan()

    except Exception as e:
        print(f"An error occurred: {e}")
    finally:
        mt5_shutdown()
        print("MT5 connection closed.")
