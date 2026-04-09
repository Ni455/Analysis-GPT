# config.py — All shared configuration for Analysis-GPT

# ── Sensibull retry settings ──────────────────────────────────────────────────
SENSIBULL_MAX_RETRIES = 3
SENSIBULL_RETRY_BASE_DELAY = 1.0   # seconds; doubled each retry (1 → 2 → 4)

# ── Reversal scanner ──────────────────────────────────────────────────────────
BUDGET_MIN    = 10_000
BUDGET_MAX    = 15_000
LOT_SIZE_MIN  = 2_000
LOT_SIZE_MAX  = 7_000
RISK_FREE     = 0.065

# ── Morning scalp ─────────────────────────────────────────────────────────────
GAP_THRESHOLD   = 1.0    # % gap to qualify as gap-up or gap-down
TREND_THRESHOLD = 2.0    # % 5d trend to qualify as trend-up or trend-down
OTM_IDEAL_MIN   = 3.0
OTM_IDEAL_MAX   = 8.0
OTM_GOOD_MAX    = 12.0
OTM_FAR_MAX     = 18.0
HIGH_OI_PCT     = 0.70
LOW_IV_THRESH   = 22.0
RATE_LIMIT_SLEEP = 0.35
MIN_SCORE       = 8

# ── Default watchlist (used by /reversal and /scalp with no symbols) ──────────
DEFAULT_SYMBOLS = [
    "ITC", "ONGC", "KOTAKBANK", "NTPC", "ADANIPOWER",
    "BEL", "COALINDIA", "POWERGRID", "TATASTEEL", "ETERNAL",
    "HINDZINC", "WIPRO", "IOC", "JIOFIN", "VBL",
    "PFC", "UNIONBANK", "DLF", "BANKBARODA", "TATAPOWER",
    "BPCL", "PNB", "IRFC", "CANBK", "MOTHERSON",
    "INDUSTOWER", "TATAMOTORSDVR", "AMBUJACEM", "GMRAIRPORT", "GAIL",
    "IDEA", "ASHOKLEY", "BHEL", "JSWENERGY", "RECLTD",
    "ABCAPITAL", "OIL", "SWIGGY", "NHPC", "DABUR",
    "NATIONALUM", "ICICIPRULI", "NYKAA", "HINDPETRO", "NMDC",
    "FEDERALBNK", "SAIL", "BANKINDIA", "LTFH", "BIOCON",
    "YESBANK", "SUZLON", "RVNL", "IDFCFIRSTB", "PATANJALI",
    "VISHAL", "KALYANKJIL", "PETRONET", "HUDCO", "CONCOR",
    "IREDA", "DELHIVERY", "SONACOMS",
]
