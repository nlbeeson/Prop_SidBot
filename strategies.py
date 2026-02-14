import logging
from typing import List

import MetaTrader5 as mt5
from config import stocks, forex, crypto, indices, commodities  # adjust as needed
from data_provider import get_universe

logger = logging.getLogger(__name__)

# -------------------------------
# Helper — Asset Filtering
# -------------------------------
def is_tradable_symbol(symbol: str) -> bool:
    """
    Return True if a symbol should be scanned based on config flags.
    This assumes MT5 symbol names include asset class prefixes or patterns.
    Modify patterns if your tickers differ.
    """
    sym = symbol.upper()

    # Stocks: tickers with letters but no typical forex/crypto suffix
    if not stocks and all(c.isalpha() for c in sym) and len(sym) <= 5:
        return False

    # Forex: usually 6-character pairs like EURUSD, GBPJPY
    if not forex and len(sym) == 6 and sym.isalpha():
        return False

    # Crypto: most exchange crypto symbols have USD/USDT suffixes or BTC/ETH base
    if not crypto and ("USD" in sym or "BTC" in sym or "ETH" in sym):
        # crude check only; you can refine for exact formats
        return False

    # Indices: common index names like SP500, NAS100, US30, DAX40, etc.
    if not indices and any(idx in sym for idx in ["500","100","30","40","DAX","NDX"]):
        return False

    # Commodities: typical commodity suffixes
    if not commodities and any(comm in sym for comm in ["XAU","XAG","OIL","GAS"]):
        return False

    return True

# -------------------------------
# Entry Scan Logic
# -------------------------------
def run_entry_scan():
    """
    Loop through universe and call your existing entry logic only
    for symbols enabled by config.  Replace placeholder scan logic
    with your actual entry conditions/callouts.
    """
    try:
        universe: List[str] = get_universe()
        if not universe:
            logger.info("[SCAN] No universe loaded; skipping entry scan.")
            return

        count_scanned = 0
        for symbol in universe:
            if not is_tradable_symbol(symbol):
                # Skip this symbol because its asset class is disabled
                logger.debug(f"[SKIP] {symbol} skipped due to config flags.")
                continue

            # Perform your actual entry scan logic for this symbol
            count_scanned += 1
            try:
                # Example: call your existing entry scanning function
                # Replace with your own logic as needed:
                logger.info(f"[SCAN] Checking {symbol} for entry conditions.")
                # your real scan function here, e.g.:
                # evaluate_entry(symbol)
            except Exception as e:
                logger.error(f"[ERROR] Exception scanning {symbol}: {e}")

        logger.info(f"[SCAN COMPLETE] Scanned {count_scanned} tradable symbols.")

    except Exception as exc:
        logger.error(f"[ERROR] Failed during entry scan: {exc}")

# -------------------------------
# Exit Scan Logic (if exists)
# -------------------------------
def run_exit_scan():
    """
    Loop through open positions and handle exit logic.
    You likely already have this in your main code; ensure it is also
    filtered similarly based on tradability if needed.
    """
    # Example placeholder; replace with your actual exit logic
    positions = mt5.positions_get()
    if positions:
        for pos in positions:
            sym = pos.symbol
            if not is_tradable_symbol(sym):
                logger.debug(f"[EXIT SKIP] {sym} excluded from exit logic by config.")
                continue
            # your real exit logic here
            logger.info(f"[EXIT] Evaluating exit for {sym}")
