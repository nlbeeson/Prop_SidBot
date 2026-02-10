from datetime import datetime, timezone

from mt5_news_filter import is_trading_blocked


def test_news_shield():
    currencies = ['USD', 'EUR', 'GBP', 'JPY']
    blocked, reason = is_trading_blocked(currencies, buffer_minutes=5)

    print(f"🕒 Current UTC Time: {datetime.now(timezone.utc)}")
    if blocked:
        print(f"🚨 NEWS BLOCK ACTIVE: Trading for {currencies} is BLOCKED due to '{reason}'")
    else:
        print(f"🟢 CLEAR: No high-impact news detected within the 5-minute buffer.")


if __name__ == "__main__":
    test_news_shield()
