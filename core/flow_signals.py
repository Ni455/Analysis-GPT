"""
Pure signal functions for options flow analysis.
Each function receives an expiry_data dict and returns (score: int, detail: str).
score: +1 = bullish, -1 = bearish, 0 = neutral
"""
import re
from statistics import median
from typing import Optional


def signal_volume_spike(expiry_data: dict) -> tuple[int, str]:
    opts = expiry_data['options']
    all_vols = [o['CE']['volume'] for o in opts] + [o['PE']['volume'] for o in opts]
    if not all_vols or all(v == 0 for v in all_vols):
        return 0, "None detected"
    med = median(all_vols)
    if med == 0:
        med = 1  # median is 0 when most strikes have zero volume; treat as 1 to avoid ZeroDivisionError

    best_ce = max(opts, key=lambda o: o['CE']['volume'])
    best_pe = max(opts, key=lambda o: o['PE']['volume'])
    ce_multiple = best_ce['CE']['volume'] / med
    pe_multiple = best_pe['PE']['volume'] / med

    ce_spike = ce_multiple > 2.0
    pe_spike = pe_multiple > 2.0

    if ce_spike and pe_spike:
        if ce_multiple >= pe_multiple:
            return 1, f"{int(best_ce['strike'])}CE — {best_ce['CE']['volume']:,} lots ({ce_multiple:.1f}× median)"
        else:
            return -1, f"{int(best_pe['strike'])}PE — {best_pe['PE']['volume']:,} lots ({pe_multiple:.1f}× median)"
    elif ce_spike:
        return 1, f"{int(best_ce['strike'])}CE — {best_ce['CE']['volume']:,} lots ({ce_multiple:.1f}× median)"
    elif pe_spike:
        return -1, f"{int(best_pe['strike'])}PE — {best_pe['PE']['volume']:,} lots ({pe_multiple:.1f}× median)"
    return 0, "None detected"


def signal_oi_buildup(expiry_data: dict) -> tuple[int, str]:
    opts = expiry_data['options']
    total_ce = sum(o['CE']['oi'] for o in opts)
    total_pe = sum(o['PE']['oi'] for o in opts)
    total = total_ce + total_pe
    if total == 0:
        return 0, "No OI data"
    ce_pct = total_ce / total * 100
    pe_pct = total_pe / total * 100
    detail = f"CE {ce_pct:.0f}% vs PE {pe_pct:.0f}%"
    if ce_pct > 55:
        return -1, f"{detail}  → heavy call writing (resistance)"
    elif pe_pct > 55:
        return 1, f"{detail}  → heavy put writing (support)"
    return 0, f"{detail}  → balanced"


def signal_pcr(expiry_data: dict, use_oi: bool = False) -> tuple[int, str]:
    opts = expiry_data['options']
    if use_oi:
        total_ce = sum(o['CE']['oi'] for o in opts)
        total_pe = sum(o['PE']['oi'] for o in opts)
        label = "OI"
    else:
        total_ce = sum(o['CE']['volume'] for o in opts)
        total_pe = sum(o['PE']['volume'] for o in opts)
        label = "Vol"
    if total_ce == 0:
        return 0, f"PCR {label}: N/A (no CE data)"
    pcr = round(total_pe / total_ce, 3)
    if pcr > 1.3:
        return 1, f"PCR {label}: {pcr} → oversold puts (contrarian bullish)"
    elif pcr < 0.7:
        return -1, f"PCR {label}: {pcr} → oversold calls (contrarian bearish)"
    return 0, f"PCR {label}: {pcr} → neutral"


def signal_iv_anomaly(expiry_data: dict) -> tuple[int, str]:
    atm_iv = expiry_data.get('atm_iv')
    if atm_iv is None or atm_iv == 0.0:       # 0.0 would cause ZeroDivisionError in excess calc
        return 0, "IV data unavailable"
    spot = expiry_data.get('spot', 0.0)
    opts = expiry_data['options']
    threshold = atm_iv * 1.2

    best_ce_excess = 0.0
    best_ce_strike = None
    best_ce_iv = None
    best_pe_excess = 0.0
    best_pe_strike = None
    best_pe_iv = None

    for o in opts:
        strike = o['strike']
        ce_iv = o['CE'].get('iv')
        pe_iv = o['PE'].get('iv')
        # Only consider OTM strikes: OTM CE = strike > spot, OTM PE = strike < spot
        if strike > spot and ce_iv is not None and ce_iv > threshold:
            excess = ce_iv / atm_iv
            if excess > best_ce_excess:
                best_ce_excess, best_ce_strike, best_ce_iv = excess, strike, ce_iv
        if strike < spot and pe_iv is not None and pe_iv > threshold:
            excess = pe_iv / atm_iv
            if excess > best_pe_excess:
                best_pe_excess, best_pe_strike, best_pe_iv = excess, strike, pe_iv

    if best_ce_strike is not None and best_pe_strike is not None:
        if best_ce_excess >= best_pe_excess:
            pct = (best_ce_iv / atm_iv - 1) * 100
            return 1, f"{int(best_ce_strike)}CE — IV {best_ce_iv} vs ATM {atm_iv} (+{pct:.0f}%)"
        else:
            pct = (best_pe_iv / atm_iv - 1) * 100
            return -1, f"{int(best_pe_strike)}PE — IV {best_pe_iv} vs ATM {atm_iv} (+{pct:.0f}%)"
    elif best_ce_strike is not None:
        pct = (best_ce_iv / atm_iv - 1) * 100
        return 1, f"{int(best_ce_strike)}CE — IV {best_ce_iv} vs ATM {atm_iv} (+{pct:.0f}%)"
    elif best_pe_strike is not None:
        pct = (best_pe_iv / atm_iv - 1) * 100
        return -1, f"{int(best_pe_strike)}PE — IV {best_pe_iv} vs ATM {atm_iv} (+{pct:.0f}%)"
    return 0, "None detected"


def composite_score(nearest: list[int], next_: Optional[list[int]] = None) -> float:
    if next_ is None:
        return float(sum(nearest)) * 1.0
    return float(sum(nearest)) * 0.6 + float(sum(next_)) * 0.4


def verdict(composite: float) -> tuple[str, str]:
    if composite >= 2.5:
        return ("BULLISH", "HIGH")
    elif composite >= 1.0:
        return ("BULLISH", "MEDIUM")
    elif composite > 0.0:
        return ("BULLISH", "LOW")
    elif composite == 0.0:
        return ("NEUTRAL", "")
    elif composite > -1.0:
        return ("BEARISH", "LOW")
    elif composite > -2.5:
        return ("BEARISH", "MEDIUM")
    else:
        return ("BEARISH", "HIGH")


def build_key_alert(nearest_signal_results: list[tuple[int, str]]) -> str:

    # Priority order: IV Anomaly (4), Volume Spike (0), OI Buildup (1), PCR Vol (2), PCR OI (3)
    priority_order = [4, 0, 1, 2, 3]

    fired = []
    for idx in priority_order:
        score, detail = nearest_signal_results[idx]
        if score != 0:
            fired.append((idx, score, detail))
        if len(fired) == 2:
            break

    if not fired:
        return "No unusual activity detected"

    phrases = []
    for idx, score, detail in fired:
        if idx == 4:  # IV Anomaly
            phrase = "IV spike on OTM calls" if score == 1 else "IV spike on OTM puts"
        elif idx == 0:  # Volume Spike
            m = re.match(r'(\d+)[CP]E', detail)
            strike = m.group(1) if m else "?"
            phrase = f"heavy CE volume at {strike}" if score == 1 else f"heavy PE volume at {strike}"
        elif idx == 1:  # OI Buildup
            phrase = "put writing support" if score == 1 else "call writing resistance"
        else:  # PCR (idx 2 or 3)
            phrase = "high PCR (oversold puts)" if score == 1 else "low PCR (oversold calls)"
        phrases.append(phrase)

    return ", ".join(phrases)
