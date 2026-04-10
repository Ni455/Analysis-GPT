# options_flow.py
"""
Options Flow Analysis — Smart Money Signal Scanner
Usage: python options_flow.py ONGC
       python options_flow.py ONGC RELIANCE TCS
"""
import sys
import io
import math
import os
from datetime import datetime, date
from statistics import median
from pathlib import Path

import requests
import yfinance as yf
from scipy.stats import norm
from scipy.optimize import brentq


from core.flow_signals import (
    signal_volume_spike, signal_oi_buildup, signal_pcr,
    signal_iv_anomaly, composite_score, verdict, build_key_alert,
)

TICKER_MAP = {
    'NIFTY': '^NSEI', 'BANKNIFTY': '^NSEBANK',
    'FINNIFTY': 'NIFTY_FIN_SERVICE.NS',
}
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
    'Accept': 'application/json',
    'Referer': 'https://web.sensibull.com/',
}
RISK_FREE = 0.065


def _bs_price(S, K, T, r, sigma, opt):
    d1 = (math.log(S / K) + (r + 0.5 * sigma**2) * T) / (sigma * math.sqrt(T))
    d2 = d1 - sigma * math.sqrt(T)
    if opt == 'CE':
        return S * norm.cdf(d1) - K * math.exp(-r * T) * norm.cdf(d2)
    return K * math.exp(-r * T) * norm.cdf(-d2) - S * norm.cdf(-d1)


def _calc_iv(S, K, T, price, opt):
    if not price or price <= 0.05 or T <= 0:
        return None
    try:
        return round(brentq(lambda v: _bs_price(S, K, T, RISK_FREE, v, opt) - price, 0.001, 10.0) * 100, 2)
    except Exception:
        return None


def fetch_symbol_data(symbol: str) -> dict:
    """
    Returns {
        'symbol': str,
        'spot': float,
        'expiries': [expiry_data, ...]   # ordered nearest first
    }
    Raises ValueError if symbol not found.
    """
    session = requests.Session()
    r = session.get(
        f'https://api.sensibull.com/v1/instruments/{symbol.upper()}',
        headers=HEADERS, timeout=10
    )
    r.raise_for_status()
    data = r.json().get('data', [])
    if not data:
        raise ValueError(f"No data found for symbol: {symbol}")

    ticker = TICKER_MAP.get(symbol.upper(), f'{symbol.upper()}.NS')
    try:
        h = yf.Ticker(ticker).history(period="1d")
        spot = float(h["Close"].iloc[-1]) if not h.empty else 0.0
    except Exception:
        spot = 0.0

    expiries_sorted = sorted(set(i['expiry'] for i in data))
    expiry_list = expiries_sorted[:2]  # nearest + next only

    result_expiries = []
    for expiry in expiry_list:
        exp_dt = datetime.strptime(expiry, '%Y-%m-%d').date()
        T = max((exp_dt - date.today()).days, 1) / 365.0

        exp_instruments = [i for i in data if i['expiry'] == expiry]
        ce_map = {i['strike']: i for i in exp_instruments if i['instrument_type'] == 'CE'}
        pe_map = {i['strike']: i for i in exp_instruments if i['instrument_type'] == 'PE'}
        strikes = sorted(set(ce_map) | set(pe_map))

        options = []
        for k in strikes:
            ce = ce_map.get(k, {})
            pe = pe_map.get(k, {})
            ce_ltp = ce.get('last_price', 0) or 0
            pe_ltp = pe.get('last_price', 0) or 0
            options.append({
                'strike': float(k),
                'CE': {
                    'volume': int(ce.get('volume', 0) or 0),
                    'oi': int(ce.get('oi', 0) or 0),
                    'last_price': ce_ltp,
                    'iv': _calc_iv(spot, k, T, ce_ltp, 'CE') if spot else None,
                },
                'PE': {
                    'volume': int(pe.get('volume', 0) or 0),
                    'oi': int(pe.get('oi', 0) or 0),
                    'last_price': pe_ltp,
                    'iv': _calc_iv(spot, k, T, pe_ltp, 'PE') if spot else None,
                },
            })

        # ATM IV = IV at strike nearest to spot
        atm_iv = None
        if spot and options:
            atm_opt = min(options, key=lambda o: abs(o['strike'] - spot))
            atm_iv = atm_opt['CE'].get('iv') or atm_opt['PE'].get('iv')

        result_expiries.append({
            'expiry': expiry,
            'spot': spot,       # included so signal_iv_anomaly can filter OTM strikes
            'atm_iv': atm_iv,
            'options': options,
        })

    return {'symbol': symbol.upper(), 'spot': spot, 'expiries': result_expiries}


def _score_label(score: int) -> str:
    if score == 1:
        return "BULLISH"
    if score == -1:
        return "BEARISH"
    return "NEUTRAL"


def _run_signals(expiry_data: dict) -> tuple[list[tuple[int, str]], list[int]]:
    """Returns (signal_results, scores).
    signal_results order matches build_key_alert contract: [vs, oi, pcrv, pcro, iv]
    (index 0=VolSpike, 1=OIBuildup, 2=PCRVol, 3=PCroi, 4=IVAnomaly)
    """
    vs   = signal_volume_spike(expiry_data)
    oi   = signal_oi_buildup(expiry_data)
    pcrv = signal_pcr(expiry_data, use_oi=False)
    pcro = signal_pcr(expiry_data, use_oi=True)
    iv   = signal_iv_anomaly(expiry_data)
    results = [vs, oi, pcrv, pcro, iv]
    scores  = [r[0] for r in results]
    return results, scores


def format_symbol_block(symbol_data: dict) -> tuple[str, str, str]:
    symbol  = symbol_data['symbol']
    spot    = symbol_data['spot']
    expiries = symbol_data['expiries']
    now     = datetime.now().strftime('%d-%b-%Y %H:%M')
    W = 44

    lines = []
    lines.append('═' * W)
    lines.append(f'  OPTIONS FLOW ANALYSIS — {symbol}')
    lines.append(f'  Spot: ₹{spot:,.2f}  |  {now}')
    lines.append('═' * W)

    all_scores = []
    nearest_results = None

    for idx, exp_data in enumerate(expiries):
        label = "(Nearest)" if idx == 0 else "(Next)"
        lines.append(f'\n── EXPIRY: {exp_data["expiry"]} {label} ' + '─' * 6)
        results, scores = _run_signals(exp_data)
        all_scores.append(scores)
        if idx == 0:
            nearest_results = results

        vs_s,  vs_d   = results[0]
        oi_s,  oi_d   = results[1]
        pcrv_s, pcrv_d = results[2]
        pcro_s, pcro_d = results[3]
        iv_s,  iv_d   = results[4]

        lines.append(f'  PCR Volume     : {pcrv_d.split(":")[1].strip() if ":" in pcrv_d else pcrv_d}  → {_score_label(pcrv_s)}')
        lines.append(f'  PCR OI         : {pcro_d.split(":")[1].strip() if ":" in pcro_d else pcro_d}  → {_score_label(pcro_s)}')
        lines.append(f'  OI Buildup     : {oi_d}')
        spike_flag = " ⚠" if vs_s != 0 else ""
        lines.append(f'  Volume Spike   : {vs_d}{spike_flag}')
        iv_flag = " ⚠" if iv_s != 0 else ""
        lines.append(f'  IV Anomaly     : {iv_d}{iv_flag}')

    # Composite score
    if not all_scores:
        return '\n'.join(lines), "NEUTRAL", ""
    nearest_scores = all_scores[0]
    next_scores    = all_scores[1] if len(all_scores) > 1 else None
    comp = composite_score(nearest_scores, next_scores)
    dirn, conf = verdict(comp)
    arrow = "▲" if dirn == "BULLISH" else ("▼" if dirn == "BEARISH" else "◆")
    alert = build_key_alert(nearest_results)
    raw_score = sum(nearest_scores)

    lines.append('\n' + '━' * W)
    lines.append('  SMART MONEY VERDICT')
    lines.append(f'  Signal     : {arrow} {dirn}')
    lines.append(f'  Confidence : {conf}  (score: {raw_score:+d}/5)')
    lines.append(f'  Key Alert  : {alert}')
    lines.append('━' * W)

    return '\n'.join(lines), dirn, conf


def format_summary_table(results: list[tuple[str, str, str]]) -> str:
    """results: list of (symbol, verdict, confidence)"""
    if len(results) < 2:
        return ""
    lines = ['\nSUMMARY']
    for symbol, dirn, conf in results:
        arrow = "▲" if dirn == "BULLISH" else ("▼" if dirn == "BEARISH" else "◆")
        conf_str = f'  ({conf})' if conf else ''
        lines.append(f'  {symbol:<12} → {arrow} {dirn}{conf_str}')
    return '\n'.join(lines)


def main():
    if hasattr(sys.stdout, 'buffer'):
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

    if len(sys.argv) < 2:
        print("Usage: python options_flow.py SYMBOL [SYMBOL2 ...]")
        sys.exit(1)

    symbols = [s.upper() for s in sys.argv[1:]]
    summary_results = []

    for symbol in symbols:
        print(f'\nFetching {symbol}...')
        try:
            data = fetch_symbol_data(symbol)
        except Exception as e:
            print(f'  ⚠ Skipping {symbol}: {e}')
            continue

        block, dirn, conf = format_symbol_block(data)
        print(block)

        summary_results.append((symbol, dirn, conf))

    summary = format_summary_table(summary_results)
    if summary:
        print(summary)


if __name__ == '__main__':
    main()
