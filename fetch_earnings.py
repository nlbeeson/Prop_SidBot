import json
import os
from pathlib import Path

import pandas as pd
from dotenv import load_dotenv

from prop_watchlist import WATCHLIST

# --- Prop_SidBot/fetch_earnings.py ---
src_folder = Path(__file__).resolve().parent
env_path = src_folder / '.env'  # Look in the current folder

load_dotenv(dotenv_path=env_path)

ALPHAVANTAGE_API_KEY = os.getenv("ALPHAVANTAGE_API_KEY")


def update_earnings_cache():
    base_path = Path(__file__).parent.resolve()
    cache_path = base_path / 'earnings_cache.json'

    url = f'https://www.alphavantage.co/query?function=EARNINGS_CALENDAR&horizon=3month&apikey={ALPHAVANTAGE_API_KEY}'

    # --- DEBUG ADDITIONS ---
    print(f"Env Path: {env_path} (Exists: {env_path.exists()})")
    print(f"API Key Loaded: {'✅ Yes' if ALPHAVANTAGE_API_KEY else '❌ No'}")
    print(f"Watchlist Count: {len(WATCHLIST)}")

    try:
        df = pd.read_csv(url)
        # Filter for only the tickers you care about
        df = df[df['symbol'].isin(WATCHLIST)]

        # Create a simple dict: {"AAPL": "2026-02-01", ...}
        earnings_map = dict(zip(df['symbol'], df['reportDate']))

        with open(cache_path, 'w') as f:
            json.dump(earnings_map, f)

        print(f"✅ Cached earnings for {len(earnings_map)} watchlist tickers.")
    except Exception as e:
        print(f"❌ Failed to fetch Alpha Vantage data: {e}")


def cleanup_old_files():
    """Removes temporary chart images and extra artifacts."""
    base_path = Path(__file__).parent.resolve()

    # 1. Clean up any orphaned .png files (from advisor scans)
    for img in base_path.glob("*.png"):
        try:
            os.remove(img)
            print(f"cleaned: {img.name}")
        except Exception as e:
            print(f"Error removing {img.name}: {e}")

    # 2. Add any other temporary files here (e.g., .txt if applicable)


def weekly_maintenance():
    """Wrapper to run all weekly administrative tasks."""
    update_earnings_cache()
    cleanup_old_files()


if __name__ == "__main__":
    update_earnings_cache()
