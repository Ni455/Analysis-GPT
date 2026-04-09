"""
Reversal Options Scanner — Reversal Trade Finder
Strategy: Find NSE stocks showing trend momentum → identify next-month PE/CE
          within budget for a reversal/continuation play.

Usage (as module):
  from core.reversal_scan import run_scan
  report = run_scan(["ONGC", "ITC"])
"""
import requests
import math
import time
import io

from scipy.stats import norm
from scipy.optimize import brentq
import yfinance as yf
from datetime import datetime, date

from config import (
    BUDGET_MIN, BUDGET_MAX, LOT_SIZE_MIN, LOT_SIZE_MAX,
    RISK_FREE, RATE_LIMIT_SLEEP,
)

# ── Helpers ───────────────────────────────────────────────────────────────────
session  = requests.Session()
HEADERS  = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Accept": "application/json",
    "Referer": "https://web.sensibull.com/",
}

def fetch_instruments(symbol):
    try:
        r = session.get(
            f"https://api.sensibull.com/v1/instruments/{symbol}",
            headers=HEADERS, timeout=15
        )
        return r.json().get("data", [])
    except Exception as e:
        return []

def get_spot_trend(symbol):
    """Return (spot, 5d_change_pct, volume_ratio_vs_avg, today_change_pct)."""
    try:
        t = yf.Ticker(f"{symbol}.NS")
        hist = t.history(period="10d")
        if hist.empty or len(hist) < 2:
            return None, None, None, None
        spot       = float(hist["Close"].iloc[-1])
        prev_close = float(hist["Close"].iloc[-2])
        today_chg  = (spot - prev_close) / prev_close * 100
        base       = float(hist["Close"].iloc[0])
        chg_5d     = (spot - base) / base * 100
        avg_vol    = float(hist["Volume"].mean())
        today_vol  = float(hist["Volume"].iloc[-1])
        vol_ratio  = today_vol / avg_vol if avg_vol > 0 else 1.0
        return spot, chg_5d, vol_ratio, today_chg
    except Exception:
        return None, None, None, None

def next_month_expiry(instruments):
    """Return the first expiry date that falls in the next calendar month."""
    today = date.today()
    if today.month == 12:
        nm_start = today.replace(year=today.year + 1, month=1, day=1)
    else:
        nm_start = today.replace(month=today.month + 1, day=1)

    expiries = sorted(set(i["expiry"] for i in instruments))
    for e in expiries:
        if datetime.strptime(e, "%Y-%m-%d").date() >= nm_start:
            return e
    return expiries[-1] if expiries else None   # fallback: furthest expiry

def bs_price(S, K, T, r, sigma, opt):
    d1 = (math.log(S / K) + (r + 0.5 * sigma ** 2) * T) / (sigma * math.sqrt(T))
    d2 = d1 - sigma * math.sqrt(T)
    if opt == "CE":
        return S * norm.cdf(d1) - K * math.exp(-r * T) * norm.cdf(d2)
    return K * math.exp(-r * T) * norm.cdf(-d2) - S * norm.cdf(-d1)

def calc_iv(S, K, T, r, price, opt):
    if price <= 0.05 or T <= 0:
        return None
    try:
        return round(brentq(lambda v: bs_price(S, K, T, r, v, opt) - price, 0.001, 10.0) * 100, 2)
    except Exception:
        return None

# ── Per-symbol scan ───────────────────────────────────────────────────────────
def scan(symbol):
    instruments = fetch_instruments(symbol)
    if not instruments:
        return []

    spot, chg_5d, vol_ratio, today_chg = get_spot_trend(symbol)
    if spot is None:
        return []

    expiry = next_month_expiry(instruments)
    if not expiry:
        return []

    expiry_dt = datetime.strptime(expiry, "%Y-%m-%d").date()
    T = max((expiry_dt - date.today()).days, 1) / 365.0

    data   = [i for i in instruments if i["expiry"] == expiry]
    ce_map = {i["strike"]: i for i in data if i["instrument_type"] == "CE"}
    pe_map = {i["strike"]: i for i in data if i["instrument_type"] == "PE"}
    strikes = sorted(set(ce_map) | set(pe_map))
    if not strikes:
        return []

    # Lot size — grab from any instrument for this symbol/expiry
    sample   = (list(ce_map.values()) + list(pe_map.values()))[0]
    lot_size = int(sample.get("lot_size", 0))
    if not lot_size or not (LOT_SIZE_MIN <= lot_size <= LOT_SIZE_MAX):
        return []

    atm     = min(strikes, key=lambda k: abs(k - spot))
    atm_idx = strikes.index(atm)
    window  = strikes[max(0, atm_idx - 12) : atm_idx + 13]

    # PCR for directional context
    total_ce_oi = sum(int(ce_map[k].get("oi", 0)) for k in ce_map)
    total_pe_oi = sum(int(pe_map[k].get("oi", 0)) for k in pe_map)
    pcr = round(total_pe_oi / total_ce_oi, 3) if total_ce_oi else 1.0

    candidates = []

    for k in window:
        # Decide which side to evaluate
        # Primary logic: uptrend → PE (reversal down bet); downtrend → CE (reversal up bet)
        # We evaluate BOTH sides so the analyst can choose
        for opt_type in ("PE", "CE"):
            opt_map = pe_map if opt_type == "PE" else ce_map
            opt = opt_map.get(k)
            if not opt:
                continue

            ltp = float(opt.get("last_price", 0) or 0)
            if ltp <= 0:
                continue

            lot_cost = round(ltp * lot_size, 2)
            if not (BUDGET_MIN <= lot_cost <= BUDGET_MAX):
                continue

            oi  = int(opt.get("oi", 0))
            vol = int(opt.get("volume", 0))
            iv  = calc_iv(spot, k, T, RISK_FREE, ltp, opt_type)

            # Distance from ATM
            if opt_type == "PE":
                dist_pct = (spot - k) / spot * 100   # positive = OTM for PE
            else:
                dist_pct = (k - spot) / spot * 100   # positive = OTM for CE

            # ── Scoring ──────────────────────────────────────────────────────
            score   = 0
            reasons = []

            # 1. Trend alignment (most important)
            if opt_type == "PE" and chg_5d > 2:
                score += 3
                reasons.append(f"Stock up {chg_5d:+.1f}% in 5d → reversal PE signal")
            elif opt_type == "CE" and chg_5d < -2:
                score += 3
                reasons.append(f"Stock down {chg_5d:+.1f}% in 5d → bounce CE signal")
            elif opt_type == "PE" and 0 < chg_5d <= 2:
                score += 1
                reasons.append(f"Stock slightly up {chg_5d:+.1f}% in 5d")
            elif opt_type == "CE" and -2 <= chg_5d < 0:
                score += 1
                reasons.append(f"Stock slightly down {chg_5d:+.1f}% in 5d")
            else:
                # Wrong direction for this option type — still include but low score
                reasons.append(f"Trend ({chg_5d:+.1f}%) not aligned with {opt_type}")

            # 2. Strike proximity (sweet spot: 5–12% OTM)
            if 3 <= dist_pct <= 8:
                score += 3
                reasons.append(f"Ideal OTM distance: {dist_pct:.1f}%")
            elif 8 < dist_pct <= 12:
                score += 2
                reasons.append(f"Good OTM distance: {dist_pct:.1f}%")
            elif 12 < dist_pct <= 18:
                score += 1
                reasons.append(f"Far OTM: {dist_pct:.1f}% — needs strong move")
            elif dist_pct < 3:
                score += 1
                reasons.append(f"Very near ATM: {dist_pct:.1f}% — high delta, expensive")
            else:
                reasons.append(f"Too far OTM: {dist_pct:.1f}% — low probability")

            # 3. Budget efficiency
            if 13_000 <= lot_cost <= 15_000:
                score += 2
                reasons.append(f"₹{lot_cost:,.0f} — strong premium, good conviction")
            elif 10_000 <= lot_cost < 13_000:
                score += 1
                reasons.append(f"₹{lot_cost:,.0f} — within budget")

            # 4. Volume momentum
            if vol_ratio >= 2.0:
                score += 2
                reasons.append(f"Volume surge: {vol_ratio:.1f}x avg → strong momentum")
            elif vol_ratio >= 1.3:
                score += 1
                reasons.append(f"Above-avg volume: {vol_ratio:.1f}x avg")

            # 5. PCR context
            if opt_type == "PE" and pcr < 0.7:
                score += 1
                reasons.append(f"PCR {pcr} < 0.7 → excessive call writing = PE edge")
            elif opt_type == "CE" and pcr > 1.2:
                score += 1
                reasons.append(f"PCR {pcr} > 1.2 → excessive put writing = CE edge")

            # 6. IV (cheap = better risk/reward)
            if iv and iv < 22:
                score += 1
                reasons.append(f"Low IV: {iv}% → relatively cheap option")

            candidates.append({
                "symbol":    symbol,
                "expiry":    expiry,
                "strike":    k,
                "type":      opt_type,
                "ltp":       ltp,
                "lot_size":  lot_size,
                "lot_cost":  lot_cost,
                "oi":        oi,
                "volume":    vol,
                "iv":        iv,
                "spot":      spot,
                "chg_5d":    chg_5d,
                "today_chg": today_chg,
                "vol_ratio": vol_ratio,
                "pcr":       pcr,
                "dist_pct":  dist_pct,
                "score":     score,
                "reasons":   reasons,
            })

    return candidates


# ── Public API ────────────────────────────────────────────────────────────────
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
