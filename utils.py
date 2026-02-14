import MetaTrader5 as mt5
from config import CATEGORY_MAP
import csv
from datetime import datetime
from pathlib import Path


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
        if "COMMODITY" in path or "OIL" in path or "ENERGY" in path: return "COMMODITIES"
        if "CRYPTO" in path: return "CRYPTO"
    return "FOREX"


def get_base_quote(symbol):
    """Extracts base and quote currencies, handling suffixes and different lengths."""
    info = mt5.symbol_info(symbol)
    if info is None:
        # Fallback for 6-char forex pairs if info not available
        if len(symbol) >= 6:
            return symbol[:3], symbol[3:6]
        return symbol, ""

    if hasattr(info, 'currency_base') and info.currency_base:
        return info.currency_base, info.currency_profit

    # Fallback to standard Forex logic for 6-char pairs if currency info is missing
    if len(symbol) >= 6 and get_symbol_category(symbol) == "FOREX":
        # Handle suffixes like EURUSD.pro by taking first 6 alpha chars if possible
        import re
        match = re.match(r'^([A-Z]{3})([A-Z]{3})', symbol.upper())
        if match:
            return match.group(1), match.group(2)
        return symbol[:3], symbol[3:6]
    
    # For non-forex, base is usually the symbol itself or currency_base if it exists
    return symbol, info.currency_profit if hasattr(info, 'currency_profit') else ""


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