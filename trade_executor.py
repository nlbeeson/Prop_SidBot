import MetaTrader5 as mt5
import logging
from config import *
from utils import log_event, get_base_quote

logger = logging.getLogger("MT5MasterControl")


def execute_mt5_trade(pick):
    symbol = pick['ticker']
    info = mt5.symbol_info(symbol)
    if info is None: return

    # 1. Filling Mode Logic
    if info.filling_mode & 1:
        filling_type = mt5.ORDER_FILLING_FOK
    elif info.filling_mode & 2:
        filling_type = mt5.ORDER_FILLING_IOC
    else:
        filling_type = mt5.ORDER_FILLING_RETURN

    # 2. Spread Calculation
    tick = mt5.symbol_info_tick(symbol)
    if tick is None: return

    pip_unit = 10 ** - (info.digits - 1)
    current_spread = (tick.ask - tick.bid) / pip_unit

    if current_spread > MAX_SPREAD_PIPS:
        logger.warning(f"⚠️ Spread too high for {symbol}: {current_spread:.1f}")
        log_event({
            "symbol": symbol, "action": "SKIP", "status": "HIGH_SPREAD",
            "spread_pips": round(current_spread, 2), "comment": "Spread Filter"
        })
        return

    # 3. Dynamic Risk and Equity
    effective_risk_pct = RISK_PER_TRADE_PCT * pick.get('risk_modifier', 1.0)
    equity = mt5.account_info().equity
    risk_cash = equity * effective_risk_pct

    # 4. CROSS-PAIR CONVERSION LOGIC
    # The risk per pip is natively in the quote currency (e.g., GBP for EURGBP)
    price_dist = abs(pick['price'] - pick['stop_price'])
    if price_dist == 0: return

    base_risk_per_lot = price_dist * info.trade_contract_size
    _, quote_currency = get_base_quote(symbol)

    conversion_rate = 1.0
    if quote_currency and quote_currency != "USD":
        # Search for a conversion pair (e.g., if quote is GBP, we need GBPUSD)
        conv_symbol = f"{quote_currency}USD"
        conv_tick = mt5.symbol_info_tick(conv_symbol)

        if conv_tick is not None:
            conversion_rate = conv_tick.bid
        else:
            # Try the inverse (e.g., if quote is JPY, we need USDJPY)
            conv_symbol = f"USD{quote_currency}"
            conv_tick = mt5.symbol_info_tick(conv_symbol)
            if conv_tick is not None and conv_tick.bid != 0:
                conversion_rate = 1.0 / conv_tick.bid
            else:
                logger.error(f"❌ Conversion failed for {symbol}. Blocking trade.")
                return

    # 5. Final Lot Sizing
    # raw_lots = USD Risk / (Quote Risk per Lot * Quote-to-USD rate)
    raw_lots = risk_cash / (base_risk_per_lot * conversion_rate)

    # Step-size normalization
    lot = round(raw_lots / info.volume_step) * info.volume_step
    lot = max(info.volume_min, min(info.volume_max, lot))

    # 6. Send Order
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

    # 7. Log Result
    status = "SUCCESS" if result.retcode == mt5.TRADE_RETCODE_DONE else f"FAIL_{result.retcode}"
    log_event({
        "symbol": symbol, "action": "BUY" if order_type == 0 else "SELL",
        "status": status, "lots": round(lot, 2), "price": price,
        "sl": pick['stop_price'], "spread_pips": round(current_spread, 2),
        "comment": result.comment if result else "No Result"
    })

    if result.retcode == mt5.TRADE_RETCODE_DONE:
        logger.info(f"✅ Trade executed: {symbol} ({lot} lots) at {price}")
    else:
        logger.error(f"❌ Trade failed: {result.comment}")


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
        if info is None:
            logger.error(f"❌ Could not get symbol info for {symbol} during close.")
            return

        for pos in positions:
            if pos.magic != MAGIC_NUMBER: continue  # Skip manual trades

            if info.filling_mode & 1:
                filling_type = mt5.ORDER_FILLING_FOK
            elif info.filling_mode & 2:
                filling_type = mt5.ORDER_FILLING_IOC
            else:
                filling_type = mt5.ORDER_FILLING_RETURN

            tick = mt5.symbol_info_tick(symbol)
            if tick is None:
                logger.error(f"❌ Could not get tick info for {symbol} during close.")
                continue

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
                "magic": MAGIC_NUMBER,
                "comment": "Bot Exit",
                "type_time": mt5.ORDER_TIME_GTC,
                "type_filling": filling_type,  # Immediate or Cancel
            }
            result = mt5.order_send(request)
            if result is None:
                logger.error(f"❌ order_send returned None for {symbol}")
            elif result.retcode != mt5.TRADE_RETCODE_DONE:
                logger.error(f"❌ Failed to close {symbol}: {result.comment} (retcode: {result.retcode})")
