import os

from dotenv import load_dotenv

load_dotenv()

# --- CREDENTIALS ---
MT5_LOGIN = int(os.getenv("MT5_LOGIN"),0)
MT5_PASSWORD = os.getenv("MT5_PASSWORD")
MT5_SERVER = os.getenv("MT5_SERVER")
MAGIC_NUMBER = os.getenv("MAGIC_NUMBER")
RESEND_API_KEY = os.getenv("RESEND_API_KEY")
EMAIL_SENDER = os.getenv("EMAIL_SENDER")
EMAIL_RECEIVER = os.getenv("EMAIL_RECEIVER", "").split(',')
ADMIN_EMAIL = os.getenv("ADMIN_EMAIL")

# --- TRADABLE INSTRUMENT TOGGLES ---
TRADE_SETTINGS = {
    "FOREX": True, "STOCKS": True, "METALS": True,
    "INDICES": True, "CRYPTO": False
}

# --- STRATEGY & RISK ---
TRADE_ALLOWED = True  # Set to False for manual review/signal-only mode
ALLOW_SHORTS = True
SIGNAL_DAYS = 21
RISK_PER_TRADE_PCT = 0.005  # 0.5%
MAX_POSITIONS = 3
MAX_DAILY_DRAWDOWN_PCT = 0.04
MAX_SPREAD_PIPS = 3.5
NEWS_BUFFER_MINUTES = 5
# --- CORRELATION & BUCKET SETTINGS FOR FOREX PAIRS ---
# Set to 'BLOCK' for prop firm safety or 'REDUCE' for retail growth
CORRELATION_MODE = 'BLOCK'
# Max allowed trades sharing a single currency (e.g., 2 USD trades)
MAX_CURRENCY_EXPOSURE = 2
# Multiplier for 'REDUCE' mode (e.g., 0.5 cuts risk in half)
CORRELATION_RISK_MODIFIER = 0.5

# --- CATEGORY LOGIC ---
VOLATILITY_MULT = {
    "FOREX": 1.5, "METALS": 2.0, "STOCKS": 2.5,
    "INDICES": 2.0, "CRYPTO": 3.0
}

CATEGORY_MAP = {
    "XAU": "METALS", "XAG": "METALS",
    "BTC": "CRYPTO", "ETH": "CRYPTO",
    "US30": "INDICES", "NAS100": "INDICES", "SPX500": "INDICES"
}

# --- SCHEDULING ---
EXIT_CHECK_INTERVAL = 300  # 5 Minutes
TRAILING_STOP_INTERVAL = 60  # 1 Minute
