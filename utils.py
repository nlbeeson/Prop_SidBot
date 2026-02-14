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
    return "FOREX"


def get_base_quote(symbol):
    """Extracts base and quote currencies, handling suffixes and different lengths."""
    info = mt5.symbol_info(symbol)
    if info is None:
        # Fallback for 6-char forex pairs if info not available
        if len(symbol) >= 6:
            return symbol[:3], symbol[3:6]
        return symbol, ""

    # Try to get from symbol info if available (some brokers provide this)
    # If not, use standard Forex logic for 6-char pairs
    if len(symbol) >= 6 and get_symbol_category(symbol) == "FOREX":
        # Handle suffixes like EURUSD.pro
        clean_symbol = symbol.replace(".", "").replace("_", "")
        # This is still a bit of a guess, but better than hardcoded indices
        # Most forex is 6 chars + suffix
        return symbol[:3], symbol[3:6]
    
    # For non-forex, base is usually the symbol itself
    return symbol, ""


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