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
