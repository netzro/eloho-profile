import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

BASE_DIR = Path(__file__).parent.parent
DB_PATH = BASE_DIR / "data" / "eloho.db"
LOG_PATH = BASE_DIR / "log.md"

NGXPULSE_API_KEY = os.getenv("NGXPULSE_API_KEY", "")
STRIPE_API_KEY = os.getenv("STRIPE_API_KEY", "")
STRIPE_CUSTOMER_ID = os.getenv("STRIPE_CUSTOMER_ID", "")
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "")

_raw_budget = int(os.getenv("MONTHLY_BUDGET", "40000"))
if _raw_budget <= 0:
    raise ValueError(f"MONTHLY_BUDGET must be positive, got {_raw_budget}")
MONTHLY_BUDGET = _raw_budget

# ── DCA Config (hardcoded — secrets only in .env) ──────────────────────

STOCKS = [
    "GTCO",
    "ZENITHBANK",
    "OKOMUOIL",
    "TRANSCORP",
    "MTNN",
    "ACCESSCORP",
    "FIDSON",
]

TARGET_UNITS = {
    "GTCO": 500,
    "ZENITHBANK": 500,
    "OKOMUOIL": 30,
    "MTNN": 50,
    "TRANSCORP": 200,
    "ACCESSCORP": 200,
    "FIDSON": 200,
}

# Derive weights from target units (proportional, auto-updates if targets change)
_TOTAL_TARGET = sum(TARGET_UNITS.values())
STOCK_WEIGHTS = {t: u / _TOTAL_TARGET for t, u in TARGET_UNITS.items()}

LIMIT_GUARD_PCT = 0.5

NGXPULSE_BASE_URL = "https://api.ngxpulse.com/v1"
