# Instrument watchlist for 5ers Prop Firm
# Tickers grouped by category
WATCHLIST_SECTORS = {
    'Forex': [
        'GBPNZD', 'GBPJPY', 'EURNZD', 'CHFJPY', 'GBPAUD', 'GBPAUD', 'GBPCAD', 'GBPCHF', 'NZDJPY', 'EURCAD',
        'CADJPY', 'AUDNZD', 'AUDJPY', 'USDCHF', 'NZDCHF', 'EURAUD', 'AUDCAD', 'NZDCAD', 'EURCHF', 'AUDCHF',
        'USDJPY', 'USDCAD', 'NZDUSD', 'GBPUSD', 'EURUSD', 'EURJPY', 'CADCHF', 'AUDUSD',
    ],
    'Indices': [
        'SP500', 'JPN225', 'US30', 'DAX40', 'NAS100',
    ],
    'Metals': [
        'XAUUSD', 'XAGUSD',
    ],
    'Commodities': [
        'XTIUSD', 'XBRUSD',
    ],
    'Crypto': [
        'BTCUSD', 'ETHUSD',
    ],
    'Stocks': [
        'AAPL', 'ACN', 'ADBE', 'AMD', 'COIN', 'CRM', 'GOOG', 'HUT', 'IBM', 'INTC', 'ORCL', 'RIOT', 'ROKU', 'SMCI',
        'SMH',
        'SOXL', 'TER', 'TSM', 'XLK', 'AAL', 'AMZN', 'CAR', 'CMG', 'DKS', 'ETSY', 'EXPE', 'F', 'HD', 'LUV', 'LVS', 'MCD',
        'SBUX', 'TGT', 'TSLA', 'UAL', 'WEN', 'XLY', 'DIS', 'META', 'VZ', 'XLC', 'BAC', 'C', 'GS', 'JPM', 'LYG', 'PYPL',
        'V',
        'WFC', 'XLF', 'AMGN', 'HUM', 'PFE', 'PTH', 'STE', 'UNH', 'XLV', 'B', 'BA', 'BAH', 'CAT', 'ETN', 'FDX', 'GE',
        'MMM',
        'XLI', 'COST', 'DG', 'ELF', 'KHC', 'KO', 'MDLZ', 'PEP', 'PG', 'WMT', 'XLP', 'BKR', 'EOG', 'SLB', 'VLO', 'XLE',
        'DOW', 'FCX', 'NEM', 'XLB', 'AMT', 'AVB', 'CCI', 'PLD', 'XLRE', 'AEP', 'D', 'SO', 'XLU', 'DIA', 'IWM', 'QQQ',
        'SPY',
        'SH', 'SQQQ', 'TNA', 'TQQQ', 'TZA', 'GDX', 'GLD', 'NUGT', 'SLV', 'QYLD',
    ],
}

# Flatten list for the scanner if needed
WATCHLIST = [ticker for sector in WATCHLIST_SECTORS.values() for ticker in sector]
