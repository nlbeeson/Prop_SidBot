import alpaca_trade_api as tradeapi
from supabase import create_client
import pandas as pd
import time
from dotenv import load_dotenv
import os

load_dotenv()

# Use confirmed variable names from your .env
SUPABASE_URL = os.getenv('SUPABASE_URL')
SUPABASE_KEY = os.getenv('SUPABASE_SERVICE_KEY')
APCA_API_KEY_ID = os.getenv('APCA_API_KEY_ID')
APCA_API_SECRET_KEY = os.getenv('APCA_API_SECRET_KEY')

alpaca = tradeapi.REST(APCA_API_KEY_ID, APCA_API_SECRET_KEY, 'https://paper-api.alpaca.markets')
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

FETCH_TIERS = [('1Day', 9000), ('4Hour', 730), ('1Hour', 365), ('15Min', 180)]

FOREX_PAIRS = [
    'GBP/NZD', 'GBP/JPY', 'EUR/NZD', 'CHF/JPY', 'GBP/AUD', 'GBP/CAD', 'GBP/CHF', 'NZD/JPY',
    'EUR/CAD', 'CAD/JPY', 'AUD/NZD', 'AUD/JPY', 'USD/CHF', 'NZD/CHF', 'EUR/AUD', 'AUD/CAD',
    'NZD/CAD', 'EUR/CHF', 'AUD/CHF', 'USD/JPY', 'USD/CAD', 'NZD/USD', 'GBP/USD', 'EUR/USD',
    'EUR/JPY', 'CAD/CHF', 'AUD/USD'
]


def get_symbols():
    try:
        # Fetch all active US equities
        active_assets = alpaca.list_assets(status='active', asset_class='us_equity')

        # DEFINITIVE FILTER:
        # Tradable + Marginable (Liquidity) + Fractionable (Market Cap Proxy)
        stocks = [
            a.symbol for a in active_assets
            if a.tradable
               and a.marginable  # Only stocks you can trade on margin
               and a.fractionable  # Generally reserved for larger-cap stocks
               and a.exchange in ['NYSE', 'NASDAQ']
               and '.' not in a.symbol  # Skips preferred shares
               and len(a.symbol) <= 4  # Skips weird warrants/instruments
        ]

        stocks.sort()
        print(f"Refined list to {len(stocks)} high-quality Russell 3000 proxy symbols.")
        return stocks + FOREX_PAIRS
    except Exception as e:
        print(f"Error fetching symbols: {e}")
        return FOREX_PAIRS


def backfill_data():
    all_symbols = get_symbols()
    for idx, symbol in enumerate(all_symbols, 1):
        print(f"[{idx}/{len(all_symbols)}] {symbol}...")
        for tf, days in FETCH_TIERS:
            start = (pd.Timestamp.now() - pd.Timedelta(days=days)).strftime('%Y-%m-%d')
            try:
                # 1. Fetch data
                df = alpaca.get_bars(symbol, tf, start=start, adjustment='all').df
                if df.empty: continue

                # 2. De-duplicate at the DataFrame level first
                df = df[~df.index.duplicated(keep='last')]

                # 3. Build unique records map
                unique_records = {}
                for ts, row in df.iterrows():
                    clean_ts = ts.isoformat()
                    # VWAP fallback to Close
                    vwap = float(row.get('vw', row['close']))

                    unique_records[(symbol, clean_ts, tf)] = {
                        "symbol": symbol.replace('/', ''),
                        "timestamp": clean_ts,
                        "open": float(row['open']), "high": float(row['high']),
                        "low": float(row['low']), "close": float(row['close']),
                        "volume": int(row['volume']), "vwap": vwap, "timeframe": tf
                    }

                # 4. Modified Batch Upsert
                records = list(unique_records.values())
                for i in range(0, len(records), 500):
                    try:
                        # Use ignore_duplicates=True to skip the 21000 error
                        # This will insert new bars and skip bars that already exist
                        supabase.table("market_data").upsert(
                            records[i:i + 500],
                            on_conflict="symbol,timestamp,timeframe",
                            ignore_duplicates=True  # <--- CRITICAL CHANGE
                        ).execute()
                    except Exception as e:
                        # Log specifically which batch failed to narrow it down
                        print(f"  ! Batch Error at index {i}: {e}")

                time.sleep(0.5)
            except Exception as e:
                print(f"  ! Error {tf}: {e}")


if __name__ == "__main__":
    backfill_data()