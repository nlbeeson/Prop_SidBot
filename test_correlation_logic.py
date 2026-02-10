import pandas as pd
from config import *


# Mocking the position structure from MT5
class MockPosition:
    def __init__(self, symbol):
        self.symbol = symbol


def get_mock_currency_exposure(new_ticker, active_positions):
    """Test version of the bucket logic."""
    new_currencies = [new_ticker[:3], new_ticker[3:]]
    exposure_count = 0
    for pos in active_positions:
        active_currencies = [pos.symbol[:3], pos.symbol[3:]]
        for cur in new_currencies:
            if cur in active_currencies:
                exposure_count += 1
    return exposure_count


def run_test_scenarios():
    print(f"🧪 TESTING CORRELATION LOGIC (Mode: {CORRELATION_MODE})")
    print(f"Settings: Max Exposure: {MAX_CURRENCY_EXPOSURE} | Modifier: {CORRELATION_RISK_MODIFIER}\n")

    # Scenario 1: No exposure
    pos_1 = []
    print(f"Scenario 1: No open trades. Target: EURUSD")
    exp_1 = get_mock_currency_exposure("EURUSD", pos_1)
    print(f"Result: Exposure {exp_1} | {'✅ PASS' if exp_1 < MAX_CURRENCY_EXPOSURE else '❌ FAIL'}\n")

    # Scenario 2: Partial exposure (Under limit)
    pos_2 = [MockPosition("EURGBP")]
    print(f"Scenario 2: Open trade [EURGBP]. Target: EURUSD")
    exp_2 = get_mock_currency_exposure("EURUSD", pos_2)
    # EUR appears once
    print(f"Result: Exposure {exp_2} | {'✅ PASS' if exp_2 < MAX_CURRENCY_EXPOSURE else '❌ FAIL'}\n")

    # Scenario 3: At Limit (Triggering logic)
    pos_3 = [MockPosition("EURGBP"), MockPosition("AUDUSD")]
    print(f"Scenario 3: Open trades [EURGBP, AUDUSD]. Target: EURUSD")
    # EUR appears once, USD appears once. Total exposure for 'EURUSD' is 2.
    exp_3 = get_mock_currency_exposure("EURUSD", pos_3)

    if exp_3 >= MAX_CURRENCY_EXPOSURE:
        action = "BLOCKING" if CORRELATION_MODE == 'BLOCK' else f"REDUCING RISK to {RISK_PER_TRADE_PCT * CORRELATION_RISK_MODIFIER}%"
        print(f"Result: Exposure {exp_3} | 🛡️ {action}\n")
    else:
        print(f"Result: Exposure {exp_3} | ✅ PASS\n")


if __name__ == "__main__":
    run_test_scenarios()