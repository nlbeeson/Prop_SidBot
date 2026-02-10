import MetaTrader5 as mt5
import psutil
import os
import time


# 1. STOP THE BOT PROCESSES
def stop_bot_processes():
    print("🛑 Searching for active bot processes...")
    current_pid = os.getpid()
    for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
        try:
            # Look for python processes running 'main.py'
            if "python" in proc.info['name'].lower():
                cmdline = proc.info['cmdline']
                if cmdline and any("main.py" in arg for arg in cmdline):
                    print(f"--- Killing Bot Process [PID: {proc.info['pid']}] ---")
                    proc.kill()
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            pass


# 2. CLOSE ALL MT5 POSITIONS
def close_all_positions():
    if not mt5.initialize():
        print("❌ MT5 Initialization failed")
        return

    positions = mt5.positions_get()
    if not positions:
        print("✅ No open positions found.")
    else:
        print(f"📉 Closing {len(positions)} positions...")
        for pos in positions:
            tick = mt5.symbol_info_tick(pos.symbol)
            order_type = mt5.ORDER_TYPE_SELL if pos.type == mt5.ORDER_TYPE_BUY else mt5.ORDER_TYPE_BUY
            price = tick.bid if order_type == mt5.ORDER_TYPE_SELL else tick.ask

            # Use the dynamic filling logic we established
            info = mt5.symbol_info(pos.symbol)
            filling = mt5.ORDER_FILLING_FOK if info.filling_mode & 1 else \
                mt5.ORDER_FILLING_IOC if info.filling_mode & 2 else \
                    mt5.ORDER_FILLING_RETURN

            request = {
                "action": mt5.TRADE_ACTION_DEAL,
                "symbol": pos.symbol,
                "volume": pos.volume,
                "type": order_type,
                "position": pos.ticket,
                "price": price,
                "deviation": 20,
                "magic": pos.magic,
                "comment": "EMERGENCY KILL",
                "type_time": mt5.ORDER_TIME_GTC,
                "type_filling": filling,
            }
            result = mt5.order_send(request)
            if result.retcode != mt5.TRADE_RETCODE_DONE:
                print(f"❌ Failed to close {pos.symbol}: {result.comment}")
            else:
                print(f"✅ Closed {pos.symbol}")

    # 3. CANCEL ALL PENDING ORDERS
    orders = mt5.orders_get()
    if orders:
        print(f"🗑️ Canceling {len(orders)} pending orders...")
        for order in orders:
            request = {
                "action": mt5.TRADE_ACTION_REMOVE,
                "order": order.ticket,
            }
            mt5.order_send(request)

    mt5.shutdown()


if __name__ == "__main__":
    stop_bot_processes()
    close_all_positions()
    print("\n⚡ SYSTEM IS NOW FLAT AND OFFLINE.")