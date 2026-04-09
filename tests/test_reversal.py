import pytest
from unittest.mock import patch, MagicMock

def test_run_scan_returns_string():
    """run_scan must return a non-empty string."""
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
