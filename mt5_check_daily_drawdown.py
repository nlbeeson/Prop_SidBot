from datetime import datetime, time

import MetaTrader5 as mt5

from config import MAX_DAILY_DRAWDOWN_PCT


def is_drawdown_safe():
    """Checks if the current daily drawdown exceeds the allowed limit using MT5 history."""
    try:
        # 1. Get current account state
        account = mt5.account_info()
        if account is None:
            print("❌ Could not retrieve account info for drawdown check.")
            return False

        current_equity = account.equity

        # 2. Calculate Start-of-Day Balance
        # We fetch all deals from today's midnight to now
        today_start = datetime.combine(datetime.now().date(), time.min)
        history_deals = mt5.history_deals_get(today_start, datetime.now())

        # Sum up all realized profit, commissions, and swaps from today
        today_realized_pl = 0
        if history_deals:
            for deal in history_deals:
                today_realized_pl += (deal.profit + deal.commission + deal.fee + deal.swap)

        # The 'Start-of-Day' reference is the current balance minus what was gained/lost today
        start_of_day_balance = account.balance - today_realized_pl

        if start_of_day_balance <= 0:
            return True

        # 3. Calculate current drawdown (including floating P/L)
        current_drawdown = (start_of_day_balance - current_equity) / start_of_day_balance

        if current_drawdown >= MAX_DAILY_DRAWDOWN_PCT:
            print(f"⚠️ DRAWDOWN ALERT: Current loss ({current_drawdown:.2%}) exceeds limit.")
            return False

        return True

    except Exception as e:
        print(f"❌ Error checking drawdown: {e}")
        return False
