import MetaTrader5 as mt5

from config import MT5_LOGIN, MT5_PASSWORD, MT5_SERVER
from prop_sidbot import get_data


def test_connection():
    # Attempt to initialize connection
    if not mt5.initialize(login=MT5_LOGIN, password=MT5_PASSWORD, server=MT5_SERVER):
        print(f"❌ Connection Failed: {mt5.last_error()}")
        return

    # Check account details
    account_info = mt5.account_info()
    if account_info:
        print(f"✅ Connected to Account: {account_info.login}")
        print(f"💰 Equity: {account_info.equity} | Balance: {account_info.balance}")
        print(f"🏦 Server: {account_info.server}")
    else:
        print("❌ Could not retrieve account info.")


def test_indicators(ticker="EURUSD"):
    df = get_data(ticker)
    if df.empty:
        print(f"❌ Failed to fetch data for {ticker}")
        return

    # Calculate indicators manually for verification
    df.ta.rsi(length=14, append=True)
    df.ta.macd(append=True)

    print(f"📊 {ticker} Data Check:")
    print(df[['timestamp', 'close', 'RSI_14']].tail(3))
    print(f"✅ Indicator calculation successful for {ticker}")


if __name__ == "__main__":
    test_connection()
    test_indicators("EURUSD")
    mt5.shutdown()
