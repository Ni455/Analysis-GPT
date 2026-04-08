# Analysis-GPT Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a Telegram bot on AWS EC2 that serves `/flow`, `/reversal`, and `/scalp` commands by wiring existing analysis engines into a unified, always-on service.

**Architecture:** A single `bot.py` process runs `python-telegram-bot` v20 in polling mode. Command handlers in `handlers/` call refactored analysis functions from `core/`. Auth is enforced via a decorator that checks every update against `ALLOWED_USER_ID`. Long scans run in asyncio background tasks.

**Tech Stack:** Python 3.11, python-telegram-bot 20.x, scipy, yfinance, requests, python-dotenv, pytest

---

## File Map

| File | Status | Responsibility |
|---|---|---|
| `config.py` | CREATE | All thresholds, budgets, watchlist, retry settings |
| `core/__init__.py` | CREATE | Empty package marker |
| `core/flow_signals.py` | CREATE | Copy from skills verbatim |
| `core/options_flow.py` | CREATE | Copy from skills + remove sys.argv + fix import path |
| `core/equity_flow.py` | CREATE | Copy from skills verbatim |
| `core/reversal_scan.py` | CREATE | Refactor: wrap global code in `run_scan(symbols) -> str` |
| `core/morning_scalp.py` | CREATE | Refactor: add `run_scalp(symbols, mode) -> str`, remove email |
| `handlers/__init__.py` | CREATE | Empty package marker |
| `handlers/flow.py` | CREATE | `/flow` command handler |
| `handlers/reversal.py` | CREATE | `/reversal` command handler |
| `handlers/scalp.py` | CREATE | `/scalp` command handler |
| `bot.py` | CREATE | App entry point + `/retry`, `/status`, `/update`, `/help` |
| `requirements.txt` | CREATE | All pip dependencies |
| `.gitignore` | CREATE | Ignore `.env`, `__pycache__`, `*.pyc`, `reports/` |
| `deploy/setup.sh` | CREATE | One-shot EC2 setup script |
| `deploy/analysis-gpt.service` | CREATE | systemd unit file |
| `tests/__init__.py` | CREATE | Empty |
| `tests/test_utils.py` | CREATE | Tests for send_chunks, auth check, retry logic |

---

## Task 1: Project Scaffold

**Files:**
- Create: `Analysis-GPT/requirements.txt`
- Create: `Analysis-GPT/.gitignore`
- Create: `Analysis-GPT/core/__init__.py`
- Create: `Analysis-GPT/handlers/__init__.py`
- Create: `Analysis-GPT/tests/__init__.py`

- [ ] **Step 1: Create requirements.txt**

```
python-telegram-bot==20.7
python-dotenv==1.0.1
requests==2.31.0
yfinance==0.2.40
scipy==1.13.0
numpy==1.26.4
openpyxl==3.1.2
pytz==2024.1
pytest==8.2.0
pytest-asyncio==0.23.6
```

- [ ] **Step 2: Create .gitignore**

```
.env
__pycache__/
*.pyc
*.pyo
.pytest_cache/
core/reports/
*.log
```

- [ ] **Step 3: Create empty package markers**

Create `core/__init__.py`, `handlers/__init__.py`, and `tests/__init__.py` — all empty files.

- [ ] **Step 4: Install dependencies locally**

```bash
cd Analysis-GPT
python -m venv venv
source venv/bin/activate   # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

Expected: All packages install without errors.

- [ ] **Step 5: Commit scaffold**

```bash
git add requirements.txt .gitignore core/__init__.py handlers/__init__.py tests/__init__.py
git commit -m "chore: scaffold Analysis-GPT project structure"
```

---

## Task 2: Create config.py

**Files:**
- Create: `Analysis-GPT/config.py`

- [ ] **Step 1: Write config.py**

```python
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
```

- [ ] **Step 2: Verify import works**

```bash
python -c "from config import DEFAULT_SYMBOLS, SENSIBULL_MAX_RETRIES; print(len(DEFAULT_SYMBOLS), SENSIBULL_MAX_RETRIES)"
```

Expected: `63 3`

- [ ] **Step 3: Commit**

```bash
git add config.py
git commit -m "feat: add shared config"
```

---

## Task 3: Copy Core Analysis Modules

**Files:**
- Create: `Analysis-GPT/core/flow_signals.py`
- Create: `Analysis-GPT/core/options_flow.py`
- Create: `Analysis-GPT/core/equity_flow.py`

- [ ] **Step 1: Copy flow_signals.py verbatim**

Copy `C:/Users/LENOVO/.claude/skills/options-analysis/flow_signals.py` to `Analysis-GPT/core/flow_signals.py` without any changes.

- [ ] **Step 2: Copy equity_flow.py verbatim**

Copy `C:/Users/LENOVO/.claude/skills/options-analysis/equity_flow.py` to `Analysis-GPT/core/equity_flow.py` without any changes.

- [ ] **Step 3: Copy and fix options_flow.py**

Copy `C:/Users/LENOVO/.claude/skills/options-analysis/options_flow.py` to `Analysis-GPT/core/options_flow.py`, then make two changes:

**Change 1** — Fix the import to use the package-relative path (line ~16):
```python
# OLD:
from flow_signals import (

# NEW:
from core.flow_signals import (
```

**Change 2** — Remove the `save_report` call from `main()` and the `REPORTS_DIR` / `save_report` function entirely (the bot sends output to Telegram; no file saving needed).

Remove these lines:
```python
REPORTS_DIR = Path(__file__).parent / 'reports'

def save_report(symbol: str, content: str) -> Path:
    REPORTS_DIR.mkdir(exist_ok=True)
    ts = datetime.now().strftime('%Y%m%d_%H%M%S')
    path = REPORTS_DIR / f'options_flow_{symbol}_{ts}.txt'
    path.write_text(content, encoding='utf-8')
    return path
```

And in `main()`, remove the two lines:
```python
        report_path = save_report(symbol, block)
        print(f'\nReport saved → {report_path.relative_to(Path(__file__).parent)}')
```

- [ ] **Step 4: Verify imports resolve**

```bash
cd Analysis-GPT
python -c "from core.options_flow import fetch_symbol_data, format_symbol_block; print('OK')"
python -c "from core.flow_signals import signal_volume_spike; print('OK')"
```

Expected: `OK` on both lines.

- [ ] **Step 5: Commit**

```bash
git add core/flow_signals.py core/options_flow.py core/equity_flow.py
git commit -m "feat: add core flow analysis modules"
```

---

## Task 4: Refactor core/reversal_scan.py

**Files:**
- Create: `Analysis-GPT/core/reversal_scan.py`

The original `reversal_scan.py` runs all code at module level (global scope). We need to wrap everything in a `run_scan(symbols: list[str]) -> str` function that returns the full text output.

- [ ] **Step 1: Write the failing test**

Create `tests/test_reversal.py`:

```python
import pytest
from unittest.mock import patch, MagicMock

def test_run_scan_returns_string():
    """run_scan must return a non-empty string."""
    # We mock the network calls so the test doesn't hit live APIs
    fake_candidate = {
        "symbol": "ONGC", "expiry": "2026-05-29", "strike": 260.0,
        "type": "PE", "ltp": 3.50, "lot_size": 2800, "lot_cost": 9800.0,
        "oi": 100000, "volume": 5000, "iv": 18.0, "spot": 272.0,
        "chg_5d": 3.5, "today_chg": 0.8, "vol_ratio": 1.2,
        "pcr": 0.9, "dist_pct": 4.4, "score": 3,
        "reasons": ["Uptrend +3.5%", "Budget OK"],
    }
    with patch("core.reversal_scan.scan", return_value=[fake_candidate]):
        from core.reversal_scan import run_scan
        result = run_scan(["ONGC"])
    assert isinstance(result, str)
    assert "REVERSAL" in result
    assert "ONGC" in result
```

- [ ] **Step 2: Run test to confirm it fails**

```bash
pytest tests/test_reversal.py -v
```

Expected: `ModuleNotFoundError` or `ImportError` — `core.reversal_scan` doesn't exist yet.

- [ ] **Step 3: Write core/reversal_scan.py**

Copy `C:/Users/LENOVO/.claude/skills/reversal-options/reversal_scan.py` to `Analysis-GPT/core/reversal_scan.py`, then refactor:

1. Remove the top-level `sys.stdout` redirect lines:
```python
# REMOVE these two lines at the top:
import sys, io, ...
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
```

2. Change the imports to pull `BUDGET_MIN`, `BUDGET_MAX`, `LOT_SIZE_MIN`, `LOT_SIZE_MAX`, `RISK_FREE`, `RATE_LIMIT_SLEEP` from config instead of defining them locally:
```python
# ADD at the top after standard imports:
from config import (
    BUDGET_MIN, BUDGET_MAX, LOT_SIZE_MIN, LOT_SIZE_MAX,
    RISK_FREE, RATE_LIMIT_SLEEP,
)
```
Then remove the duplicate constant definitions that follow.

3. Wrap all the module-level scanning and printing code (everything after the `scan()` function definition and before end of file) inside a new `run_scan` function:

```python
def run_scan(symbols: list[str]) -> str:
    """Run the reversal scanner on the given symbols and return the full report as a string."""
    import io as _io
    buf = _io.StringIO()

    W = 92
    SEP = "=" * W

    def p(text=""):
        buf.write(str(text) + "\n")

    p(SEP)
    p("  REVERSAL OPTIONS SCANNER  —  REVERSAL TRADE FINDER")
    p(f"  Budget: ₹{BUDGET_MIN:,} – ₹{BUDGET_MAX:,} per lot  |  Lot size: {LOT_SIZE_MIN:,}–{LOT_SIZE_MAX:,} units")
    p(f"  Expiry: NEXT MONTH  |  Scanning {len(symbols)} symbols...")
    p(SEP)

    all_candidates = []

    for sym in symbols:
        results = scan(sym)
        if results:
            all_candidates.extend(results)
            best = max(results, key=lambda x: x["score"])
            p(f"  {sym:<18} ✓  {len(results)} budget hits  |  best: {int(best['strike'])} {best['type']} "
              f"₹{best['lot_cost']:,.0f}  score:{best['score']}")
        else:
            p(f"  {sym:<18} ✗  no budget matches")
        time.sleep(RATE_LIMIT_SLEEP)

    all_candidates.sort(key=lambda x: (x["score"], abs(x.get("chg_5d", 0))), reverse=True)

    p()
    p(SEP)
    p("  RANKED OPPORTUNITIES  (top 15)")
    p(SEP)
    p(f"  {'#':<3} {'Symbol':<14} {'Expiry':<12} {'Strike':<8} {'T':<3} {'LTP':>6} "
      f"{'Lot':>6} {'Cost':>9} {'OTM%':>6} {'5dChg':>7} {'VolX':>5} {'IV':>6} {'Score':>6}")
    p("  " + "─" * (W - 2))

    for i, c in enumerate(all_candidates[:15], 1):
        iv_s  = f"{c['iv']}%" if c["iv"] else " N/A"
        p(f"  {i:<3} {c['symbol']:<14} {c['expiry']:<12} {int(c['strike']):<8} {c['type']:<3} "
          f"{c['ltp']:>6.2f} {c['lot_size']:>6,} {c['lot_cost']:>9,.0f} "
          f"{c['dist_pct']:>5.1f}% {c['chg_5d']:>+6.1f}% {c['vol_ratio']:>4.1f}x "
          f"{iv_s:>6} {'★'*c['score']:>8}")

    p()
    p(SEP)
    p("  TOP 5 DETAILED ANALYSIS")
    p(SEP)

    for i, c in enumerate(all_candidates[:5], 1):
        direction = ("Uptrend → PE reversal bet" if c["type"] == "PE"
                     else "Downtrend → CE bounce bet")
        iv_s = f"{c['iv']}%" if c["iv"] else "N/A"
        p(f"\n  #{i}  {c['symbol']} {c['expiry']} {int(c['strike'])} {c['type']}")
        p(f"  {'─' * 55}")
        p(f"  Spot:       ₹{c['spot']:,.2f}  ({c['chg_5d']:+.1f}% past 5d,  today {c['today_chg']:+.1f}%)")
        p(f"  Strike:     ₹{int(c['strike']):,}  ({c['dist_pct']:.1f}% OTM)")
        p(f"  Option LTP: ₹{c['ltp']:.2f} / unit")
        p(f"  Lot size:   {c['lot_size']:,} units")
        p(f"  Total cost: ₹{c['lot_cost']:,.2f}  (1 lot)")
        p(f"  IV:         {iv_s}   PCR: {c['pcr']}   Vol: {c['vol_ratio']:.1f}x avg")
        p(f"  Direction:  {direction}")
        p(f"  Score:      {'★' * c['score']}  ({c['score']} pts)")
        p("  Signals:")
        for r in c["reasons"]:
            p(f"    • {r}")

    p()
    p(SEP)
    p("  ⚠  Data from last trading session. Confirm live prices on Sensibull/Zerodha.")
    p("  ⚠  Check India VIX, global cues, and news before placing any order.")
    p("  ⚠  Max 1 lot per trade. Risk only what you can afford to lose entirely.")
    p(SEP)

    return buf.getvalue()
```

Remove the old module-level print statements (everything from `print(SEP)` onward at module scope).

- [ ] **Step 4: Run test to verify it passes**

```bash
pytest tests/test_reversal.py -v
```

Expected: `PASSED`

- [ ] **Step 5: Commit**

```bash
git add core/reversal_scan.py tests/test_reversal.py
git commit -m "feat: add core reversal scanner with run_scan() function"
```

---

## Task 5: Refactor core/morning_scalp.py

**Files:**
- Create: `Analysis-GPT/core/morning_scalp.py`

The original `morning_scalp.py` sends email at the end of `main()`. We need to add a `run_scalp(symbols, mode) -> str` function that returns the report text instead of emailing it.

- [ ] **Step 1: Write the failing test**

Create `tests/test_scalp.py`:

```python
def test_run_scalp_returns_string():
    """run_scalp must return a non-empty string without sending email."""
    from unittest.mock import patch, MagicMock
    fake_cand = {
        "symbol": "ITC", "expiry": "2026-04-24", "strike": 420.0,
        "type": "PE", "ltp": 5.0, "lot_size": 3200, "lot_cost": 16000.0,
        "oi": 80000, "volume": 3000, "iv": 20.0, "spot": 440.0,
        "gap_pct": 1.5, "trend_pct": 2.5,
        "direction": {"signal": "PE", "strong": True, "gap_available": True},
        "dist_pct": 4.5, "score": 9, "reasons": ["Gap up", "Trend up"],
    }
    with patch("core.morning_scalp.scan_symbol", return_value=([fake_cand], None)):
        from core.morning_scalp import run_scalp
        result = run_scalp(["ITC"], "morning")
    assert isinstance(result, str)
    assert "ITC" in result
    assert "SCALP" in result
```

- [ ] **Step 2: Run test to confirm it fails**

```bash
pytest tests/test_scalp.py -v
```

Expected: `ModuleNotFoundError` — `core.morning_scalp` doesn't exist yet.

- [ ] **Step 3: Write core/morning_scalp.py**

Copy `C:/Users/LENOVO/.claude/skills/morning-scalp/morning_scalp.py` to `Analysis-GPT/core/morning_scalp.py`, then make these changes:

1. Update config imports — replace the `from config import (...)` block at the top with:
```python
from config import (
    GAP_THRESHOLD, TREND_THRESHOLD,
    BUDGET_MIN, BUDGET_MAX, RISK_FREE,
    OTM_IDEAL_MIN, OTM_IDEAL_MAX, OTM_GOOD_MAX, OTM_FAR_MAX,
    HIGH_OI_PCT, LOW_IV_THRESH,
    RATE_LIMIT_SLEEP,
    MIN_SCORE as MIN_EMAIL_SCORE,
)
```

2. Remove `send_email()` function entirely (we send to Telegram instead).

3. Add `run_scalp()` function after `build_email_body()`:

```python
def run_scalp(symbols: list[str], mode: str = "morning") -> str:
    """
    Scan the given symbols and return the full report as a plain-text string.
    mode: 'morning' | 'eod'
    """
    import time as _time
    all_candidates = []
    all_skipped = []

    for sym in symbols:
        cands, skip = scan_symbol(sym, mode)
        if cands:
            all_candidates.extend(cands)
        if skip:
            all_skipped.append(skip)
        _time.sleep(RATE_LIMIT_SLEEP)

    all_candidates.sort(key=lambda c: (
        c["score"],
        c.get("oi", 0),
        -(c.get("iv") or 99),
        -(c.get("dist_pct") or 99),
    ), reverse=True)

    top_candidates = [c for c in all_candidates if c["score"] >= MIN_EMAIL_SCORE]
    if not top_candidates:
        top_candidates = all_candidates[:5]

    return build_email_body(top_candidates, all_skipped, mode)
```

4. Leave `main()` intact (it's still usable for direct CLI runs).

- [ ] **Step 4: Run test to verify it passes**

```bash
pytest tests/test_scalp.py -v
```

Expected: `PASSED`

- [ ] **Step 5: Commit**

```bash
git add core/morning_scalp.py tests/test_scalp.py
git commit -m "feat: add core morning scalp with run_scalp() function"
```

---

## Task 6: Bot Utilities (auth + send_chunks + retry)

**Files:**
- Create: `Analysis-GPT/bot_utils.py`
- Create: `Analysis-GPT/tests/test_utils.py`

- [ ] **Step 1: Write the failing tests**

Create `tests/test_utils.py`:

```python
import pytest

def test_send_chunks_short_message():
    """Messages under 4096 chars yield exactly one chunk."""
    from bot_utils import split_chunks
    chunks = split_chunks("hello world")
    assert chunks == ["hello world"]

def test_send_chunks_long_message():
    """Messages over 4096 chars are split into multiple chunks."""
    from bot_utils import split_chunks
    long_msg = "A" * 5000
    chunks = split_chunks(long_msg)
    assert len(chunks) == 2
    assert all(len(c) <= 4096 for c in chunks)
    assert "".join(chunks) == long_msg

def test_send_chunks_empty():
    """Empty string returns one empty chunk."""
    from bot_utils import split_chunks
    chunks = split_chunks("")
    assert chunks == [""]

def test_is_authorized_matching_id():
    """Returns True when user_id matches ALLOWED_USER_ID."""
    from bot_utils import is_authorized
    assert is_authorized(123456, allowed_id=123456) is True

def test_is_authorized_wrong_id():
    """Returns False when user_id does not match."""
    from bot_utils import is_authorized
    assert is_authorized(999999, allowed_id=123456) is False

def test_retry_success_on_first_try():
    """retry_call returns the value when func succeeds immediately."""
    from bot_utils import retry_call
    result = retry_call(lambda: 42)
    assert result == 42

def test_retry_success_after_failures():
    """retry_call retries and returns on eventual success."""
    from bot_utils import retry_call
    attempts = {"n": 0}
    def flaky():
        attempts["n"] += 1
        if attempts["n"] < 3:
            raise ConnectionError("fail")
        return "ok"
    result = retry_call(flaky, max_retries=3, base_delay=0)
    assert result == "ok"
    assert attempts["n"] == 3

def test_retry_raises_after_max():
    """retry_call raises the last exception after max_retries exhausted."""
    from bot_utils import retry_call
    def always_fail():
        raise ConnectionError("always")
    with pytest.raises(ConnectionError):
        retry_call(always_fail, max_retries=3, base_delay=0)
```

- [ ] **Step 2: Run tests to confirm they fail**

```bash
pytest tests/test_utils.py -v
```

Expected: All `ImportError` — `bot_utils` doesn't exist yet.

- [ ] **Step 3: Write bot_utils.py**

```python
# bot_utils.py — Shared utilities for the Telegram bot
import time

TELEGRAM_MAX_CHARS = 4096


def split_chunks(text: str, max_len: int = TELEGRAM_MAX_CHARS) -> list[str]:
    """Split text into chunks of at most max_len characters."""
    if len(text) <= max_len:
        return [text]
    chunks = []
    while text:
        chunks.append(text[:max_len])
        text = text[max_len:]
    return chunks


def is_authorized(user_id: int, allowed_id: int) -> bool:
    """Return True if user_id matches the allowed user."""
    return user_id == allowed_id


def retry_call(func, max_retries: int = 3, base_delay: float = 1.0):
    """
    Call func(), retrying up to max_retries times on any exception.
    Delay doubles each retry: base_delay → 2*base_delay → 4*base_delay.
    Raises the last exception if all retries are exhausted.
    """
    last_exc = None
    for attempt in range(max_retries):
        try:
            return func()
        except Exception as e:
            last_exc = e
            if attempt < max_retries - 1:
                time.sleep(base_delay * (2 ** attempt))
    raise last_exc
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
pytest tests/test_utils.py -v
```

Expected: All 7 tests `PASSED`.

- [ ] **Step 5: Commit**

```bash
git add bot_utils.py tests/test_utils.py
git commit -m "feat: add bot utilities (auth, chunking, retry)"
```

---

## Task 7: Build handlers/flow.py

**Files:**
- Create: `Analysis-GPT/handlers/flow.py`

- [ ] **Step 1: Write handlers/flow.py**

```python
# handlers/flow.py — /flow command handler
from telegram import Update
from telegram.ext import ContextTypes

from bot_utils import split_chunks, retry_call, is_authorized
from config import SENSIBULL_MAX_RETRIES, SENSIBULL_RETRY_BASE_DELAY
from core.options_flow import fetch_symbol_data, format_symbol_block, format_summary_table


async def flow_handler(update: Update, context: ContextTypes.DEFAULT_TYPE, allowed_id: int) -> None:
    """Handle /flow SYMBOL [SYMBOL2 ...]"""
    user_id = update.effective_user.id
    if not is_authorized(user_id, allowed_id):
        return

    args = context.args
    if not args:
        await update.message.reply_text("Usage: /flow SYMBOL [SYMBOL2 ...]\nExample: /flow ONGC RELIANCE")
        return

    symbols = [s.upper() for s in args]
    await update.message.reply_text(f"⏳ Fetching flow data for: {', '.join(symbols)}...")

    summary_results = []
    error_symbols = []
    output_parts = []

    for symbol in symbols:
        try:
            data = retry_call(
                lambda s=symbol: fetch_symbol_data(s),
                max_retries=SENSIBULL_MAX_RETRIES,
                base_delay=SENSIBULL_RETRY_BASE_DELAY,
            )
            block, dirn, conf = format_symbol_block(data)
            output_parts.append(block)
            summary_results.append((symbol, dirn, conf))
        except Exception as e:
            error_symbols.append(symbol)
            output_parts.append(f"❌ {symbol}: failed after {SENSIBULL_MAX_RETRIES} retries — {e}")

    summary = format_summary_table(summary_results)
    if summary:
        output_parts.append(summary)

    full_output = "\n\n".join(output_parts)

    for chunk in split_chunks(full_output):
        await update.message.reply_text(f"```\n{chunk}\n```", parse_mode="Markdown")

    # Store last command for /retry
    context.bot_data["last_command"] = ("flow", args)
    if error_symbols:
        context.bot_data["last_error"] = ("flow", args)
        await update.message.reply_text(
            f"⚠️ Failed: {', '.join(error_symbols)}. Send /retry to try again."
        )
```

- [ ] **Step 2: Verify import resolves**

```bash
python -c "from handlers.flow import flow_handler; print('OK')"
```

Expected: `OK`

- [ ] **Step 3: Commit**

```bash
git add handlers/flow.py
git commit -m "feat: add /flow command handler"
```

---

## Task 8: Build handlers/reversal.py

**Files:**
- Create: `Analysis-GPT/handlers/reversal.py`

- [ ] **Step 1: Write handlers/reversal.py**

```python
# handlers/reversal.py — /reversal command handler
import asyncio
from telegram import Update
from telegram.ext import ContextTypes

from bot_utils import split_chunks, is_authorized
from config import DEFAULT_SYMBOLS
from core.reversal_scan import run_scan


async def reversal_handler(update: Update, context: ContextTypes.DEFAULT_TYPE, allowed_id: int) -> None:
    """Handle /reversal [SYMBOL1 SYMBOL2 ...]"""
    user_id = update.effective_user.id
    if not is_authorized(user_id, allowed_id):
        return

    args = context.args
    symbols = [s.upper() for s in args] if args else DEFAULT_SYMBOLS
    label = f"{len(symbols)} stocks" if not args else ", ".join(symbols)
    await update.message.reply_text(f"⏳ Scanning {label} for reversal opportunities...")

    try:
        # run_scan is synchronous (uses time.sleep for rate limiting); run in thread pool
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(None, run_scan, symbols)
    except Exception as e:
        await update.message.reply_text(f"❌ Reversal scan failed: {e}\nSend /retry to try again.")
        context.bot_data["last_error"] = ("reversal", list(args))
        return

    for chunk in split_chunks(result):
        await update.message.reply_text(f"```\n{chunk}\n```", parse_mode="Markdown")

    context.bot_data["last_command"] = ("reversal", list(args))
```

- [ ] **Step 2: Verify import resolves**

```bash
python -c "from handlers.reversal import reversal_handler; print('OK')"
```

Expected: `OK`

- [ ] **Step 3: Commit**

```bash
git add handlers/reversal.py
git commit -m "feat: add /reversal command handler"
```

---

## Task 9: Build handlers/scalp.py

**Files:**
- Create: `Analysis-GPT/handlers/scalp.py`

- [ ] **Step 1: Write handlers/scalp.py**

```python
# handlers/scalp.py — /scalp command handler
import asyncio
from telegram import Update
from telegram.ext import ContextTypes

from bot_utils import split_chunks, is_authorized
from core.morning_scalp import run_scalp


async def scalp_handler(update: Update, context: ContextTypes.DEFAULT_TYPE, allowed_id: int) -> None:
    """Handle /scalp SYMBOL [SYMBOL2 ...]"""
    user_id = update.effective_user.id
    if not is_authorized(user_id, allowed_id):
        return

    args = context.args
    if not args:
        await update.message.reply_text("Usage: /scalp SYMBOL [SYMBOL2 ...]\nExample: /scalp ONGC")
        return

    symbols = [s.upper() for s in args]
    await update.message.reply_text(f"⏳ Running scalp scan for: {', '.join(symbols)}...")

    try:
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(None, run_scalp, symbols, "morning")
    except Exception as e:
        await update.message.reply_text(f"❌ Scalp scan failed: {e}\nSend /retry to try again.")
        context.bot_data["last_error"] = ("scalp", list(args))
        return

    for chunk in split_chunks(result):
        await update.message.reply_text(f"```\n{chunk}\n```", parse_mode="Markdown")

    context.bot_data["last_command"] = ("scalp", list(args))
```

- [ ] **Step 2: Verify import resolves**

```bash
python -c "from handlers.scalp import scalp_handler; print('OK')"
```

Expected: `OK`

- [ ] **Step 3: Commit**

```bash
git add handlers/scalp.py
git commit -m "feat: add /scalp command handler"
```

---

## Task 10: Build bot.py

**Files:**
- Create: `Analysis-GPT/bot.py`

- [ ] **Step 1: Write bot.py**

```python
#!/usr/bin/env python3
# bot.py — Analysis-GPT Telegram Bot entry point
import asyncio
import os
import subprocess
from dotenv import load_dotenv

from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes

from bot_utils import is_authorized, split_chunks
from handlers.flow import flow_handler
from handlers.reversal import reversal_handler
from handlers.scalp import scalp_handler

load_dotenv()

BOT_TOKEN   = os.environ["BOT_TOKEN"]
ALLOWED_ID  = int(os.environ["ALLOWED_USER_ID"])

HELP_TEXT = """
Analysis-GPT Commands:

/flow SYMBOL [SYMBOL2 ...]
  Options flow smart money analysis
  Example: /flow ONGC RELIANCE

/reversal [SYMBOL ...]
  Reversal trade scanner
  No symbols = scans full 63-stock watchlist
  Example: /reversal ONGC TATASTEEL

/scalp SYMBOL [SYMBOL2 ...]
  Morning scalp analysis
  Example: /scalp ONGC

/status
  Check if Sensibull and yfinance APIs are reachable

/retry
  Re-run the last failed command

/update
  Pull latest code from GitHub and restart bot

/help
  Show this message
""".strip()


async def cmd_help(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_authorized(update.effective_user.id, ALLOWED_ID):
        return
    await update.message.reply_text(HELP_TEXT)


async def cmd_status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_authorized(update.effective_user.id, ALLOWED_ID):
        return
    import requests, yfinance as yf
    results = []
    try:
        r = requests.get(
            "https://api.sensibull.com/v1/instruments/ONGC",
            headers={"User-Agent": "Mozilla/5.0", "Referer": "https://web.sensibull.com/"},
            timeout=8,
        )
        results.append(f"Sensibull API: {'✅ OK' if r.status_code == 200 else f'❌ {r.status_code}'}")
    except Exception as e:
        results.append(f"Sensibull API: ❌ {e}")
    try:
        price = yf.Ticker("ONGC.NS").fast_info["lastPrice"]
        results.append(f"yfinance:       ✅ OK (ONGC ₹{price:.2f})")
    except Exception as e:
        results.append(f"yfinance:       ❌ {e}")
    await update.message.reply_text("\n".join(results))


async def cmd_retry(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_authorized(update.effective_user.id, ALLOWED_ID):
        return
    last_error = context.bot_data.get("last_error")
    if not last_error:
        await update.message.reply_text("No failed command to retry.")
        return
    cmd, args = last_error
    context.args = args
    if cmd == "flow":
        await flow_handler(update, context, ALLOWED_ID)
    elif cmd == "reversal":
        await reversal_handler(update, context, ALLOWED_ID)
    elif cmd == "scalp":
        await scalp_handler(update, context, ALLOWED_ID)


async def cmd_update(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_authorized(update.effective_user.id, ALLOWED_ID):
        return
    await update.message.reply_text("⏳ Pulling latest code from GitHub...")
    try:
        result = subprocess.run(
            ["git", "pull", "origin", "main"],
            capture_output=True, text=True, timeout=60,
        )
        output = result.stdout.strip() or result.stderr.strip() or "No output"
        await update.message.reply_text(f"git pull output:\n{output}")
        await update.message.reply_text("✅ Updated. Restarting bot...")
        subprocess.Popen(["sudo", "systemctl", "restart", "analysis-gpt"])
    except Exception as e:
        await update.message.reply_text(f"❌ Update failed: {e}")


async def cmd_flow(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await flow_handler(update, context, ALLOWED_ID)


async def cmd_reversal(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await reversal_handler(update, context, ALLOWED_ID)


async def cmd_scalp(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await scalp_handler(update, context, ALLOWED_ID)


def main():
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("help",     cmd_help))
    app.add_handler(CommandHandler("start",    cmd_help))
    app.add_handler(CommandHandler("status",   cmd_status))
    app.add_handler(CommandHandler("retry",    cmd_retry))
    app.add_handler(CommandHandler("update",   cmd_update))
    app.add_handler(CommandHandler("flow",     cmd_flow))
    app.add_handler(CommandHandler("reversal", cmd_reversal))
    app.add_handler(CommandHandler("scalp",    cmd_scalp))
    print("Bot started. Polling...")
    app.run_polling(drop_pending_updates=True)


if __name__ == "__main__":
    main()
```

- [ ] **Step 2: Verify import resolves (without token)**

```bash
python -c "
import os; os.environ['BOT_TOKEN']='fake'; os.environ['ALLOWED_USER_ID']='123'
import bot; print('imports OK')
" 2>&1 | grep -E "OK|Error|Import"
```

Expected: `imports OK`

- [ ] **Step 3: Commit**

```bash
git add bot.py
git commit -m "feat: add main bot.py with all command handlers"
```

---

## Task 11: Create deploy/setup.sh and systemd service

**Files:**
- Create: `Analysis-GPT/deploy/setup.sh`
- Create: `Analysis-GPT/deploy/analysis-gpt.service`

- [ ] **Step 1: Write deploy/analysis-gpt.service**

```ini
[Unit]
Description=Analysis-GPT Telegram Bot
After=network.target

[Service]
Type=simple
User=ubuntu
WorkingDirectory=/home/ubuntu/Analysis-GPT
ExecStart=/home/ubuntu/Analysis-GPT/venv/bin/python bot.py
Restart=always
RestartSec=10
EnvironmentFile=/home/ubuntu/Analysis-GPT/.env
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
```

- [ ] **Step 2: Write deploy/setup.sh**

```bash
#!/usr/bin/env bash
# deploy/setup.sh — One-shot EC2 first-time setup for Analysis-GPT
# Run as: bash setup.sh
set -e

REPO_URL="https://github.com/YOUR_USERNAME/Analysis-GPT.git"
APP_DIR="/home/ubuntu/Analysis-GPT"
SERVICE="analysis-gpt"

echo "==> Updating system packages"
sudo apt-get update -y
sudo apt-get install -y python3.11 python3.11-venv python3-pip git

echo "==> Cloning repo"
if [ -d "$APP_DIR" ]; then
  echo "   Directory exists — pulling latest"
  cd "$APP_DIR" && git pull origin main
else
  git clone "$REPO_URL" "$APP_DIR"
  cd "$APP_DIR"
fi

echo "==> Creating virtual environment"
python3.11 -m venv "$APP_DIR/venv"
"$APP_DIR/venv/bin/pip" install --upgrade pip
"$APP_DIR/venv/bin/pip" install -r "$APP_DIR/requirements.txt"

echo "==> Creating .env file"
if [ ! -f "$APP_DIR/.env" ]; then
  read -p "Enter your Telegram BOT_TOKEN: " BOT_TOKEN
  read -p "Enter your ALLOWED_USER_ID: " USER_ID
  cat > "$APP_DIR/.env" <<EOF
BOT_TOKEN=${BOT_TOKEN}
ALLOWED_USER_ID=${USER_ID}
EOF
  echo "   .env created"
else
  echo "   .env already exists — skipping"
fi

echo "==> Installing systemd service"
sudo cp "$APP_DIR/deploy/analysis-gpt.service" "/etc/systemd/system/${SERVICE}.service"
sudo systemctl daemon-reload
sudo systemctl enable "$SERVICE"
sudo systemctl restart "$SERVICE"

echo "==> Granting passwordless sudo for systemctl restart (needed by /update command)"
SUDOERS_LINE="ubuntu ALL=(ALL) NOPASSWD: /bin/systemctl restart ${SERVICE}"
if ! sudo grep -qF "$SUDOERS_LINE" /etc/sudoers; then
  echo "$SUDOERS_LINE" | sudo tee -a /etc/sudoers > /dev/null
  echo "   sudoers rule added"
fi

echo ""
echo "✅ Setup complete!"
echo "   Check bot status: sudo systemctl status ${SERVICE}"
echo "   View logs:        journalctl -u ${SERVICE} -f"
```

- [ ] **Step 3: Make setup.sh executable**

```bash
chmod +x deploy/setup.sh
```

- [ ] **Step 4: Update REPO_URL in setup.sh**

Replace `YOUR_USERNAME` in `setup.sh` with your actual GitHub username.

- [ ] **Step 5: Commit**

```bash
git add deploy/setup.sh deploy/analysis-gpt.service
git commit -m "feat: add EC2 deploy script and systemd service"
```

---

## Task 12: Run All Tests and Local Smoke Test

- [ ] **Step 1: Run full test suite**

```bash
cd Analysis-GPT
pytest tests/ -v
```

Expected output:
```
tests/test_utils.py::test_send_chunks_short_message PASSED
tests/test_utils.py::test_send_chunks_long_message PASSED
tests/test_utils.py::test_send_chunks_empty PASSED
tests/test_utils.py::test_is_authorized_matching_id PASSED
tests/test_utils.py::test_is_authorized_wrong_id PASSED
tests/test_utils.py::test_retry_success_on_first_try PASSED
tests/test_utils.py::test_retry_success_after_failures PASSED
tests/test_utils.py::test_retry_raises_after_max PASSED
tests/test_reversal.py::test_run_scan_returns_string PASSED
tests/test_scalp.py::test_run_scalp_returns_string PASSED
```

- [ ] **Step 2: Create .env for local testing**

```bash
cat > .env <<EOF
BOT_TOKEN=YOUR_REAL_BOT_TOKEN_HERE
ALLOWED_USER_ID=YOUR_TELEGRAM_USER_ID_HERE
EOF
```

Get your bot token from `@BotFather` and your user ID from `@userinfobot` in Telegram.

- [ ] **Step 3: Run bot locally and smoke test**

```bash
python bot.py
```

Expected: `Bot started. Polling...`

Open Telegram, find your bot, send:
- `/help` → should reply with command list
- `/status` → should reply with Sensibull ✅ and yfinance ✅
- `/flow ONGC` → should reply with analysis report

- [ ] **Step 4: Push to GitHub**

```bash
git remote add origin https://github.com/YOUR_USERNAME/Analysis-GPT.git
git push -u origin main
```

- [ ] **Step 5: Final commit if any fixes needed**

```bash
git add -A
git commit -m "fix: any issues found during local smoke test"
```

---

## Task 13: Deploy to EC2

- [ ] **Step 1: Launch EC2 instance**

1. AWS Console → EC2 → Launch Instance
2. Name: `analysis-gpt`
3. AMI: Ubuntu Server 22.04 LTS (Free tier eligible)
4. Instance type: `t3.micro`
5. Create a key pair (download the `.pem` file)
6. Security group: allow SSH (port 22) from your IP only — no other ports needed
7. Launch

- [ ] **Step 2: SSH into the instance**

```bash
chmod 400 your-key.pem
ssh -i your-key.pem ubuntu@<EC2_PUBLIC_IP>
```

- [ ] **Step 3: Run setup script**

```bash
curl -sSL https://raw.githubusercontent.com/YOUR_USERNAME/Analysis-GPT/main/deploy/setup.sh | bash
```

Enter your bot token and user ID when prompted.

- [ ] **Step 4: Verify bot is running**

```bash
sudo systemctl status analysis-gpt
```

Expected: `Active: active (running)`

- [ ] **Step 5: Test from Telegram**

Send `/status` to your bot in Telegram. Should reply with API health.
Send `/flow ONGC` — should return the full flow analysis.

- [ ] **Step 6: Test /update workflow**

Make a small change locally (e.g. add a comment to config.py), push to GitHub, then send `/update` to the bot. It should pull and restart automatically.

---

## Post-Deploy Reference

```
View live logs:           journalctl -u analysis-gpt -f
Restart manually:         sudo systemctl restart analysis-gpt
Stop bot:                 sudo systemctl stop analysis-gpt
Update code remotely:     /update (from Telegram)
Update code via SSH:      git pull origin main && sudo systemctl restart analysis-gpt
```
