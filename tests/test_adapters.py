"""Tests for the framework adapters.

Adapters must not import the target framework at the top level, so all tests
use mock objects that mimic the framework APIs.  The critical invariant is:
every adapter must extract returns, call robustness_report, and return a dict
with the standard keys (score, verdict, statistics, red_flags, checklist).
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

# ── helpers ─────────────────────────────────────────────────────────────────

def _equity(n: int = 300, seed: int = 1) -> np.ndarray:
    rng = np.random.default_rng(seed)
    r = rng.normal(0.0005, 0.01, n)
    return np.cumprod(1 + r) * 100.0


def _returns(n: int = 300, seed: int = 1) -> np.ndarray:
    rng = np.random.default_rng(seed)
    return rng.normal(0.0005, 0.01, n)


def _assert_report(report):
    assert isinstance(report, dict)
    assert "score" in report and 0 <= report["score"] <= 100
    assert "verdict" in report and report["verdict"] in ("robust", "fragile", "likely_overfit")
    assert "statistics" in report
    assert "red_flags" in report
    assert "checklist" in report


# ── audit_returns (base) ─────────────────────────────────────────────────────

class TestAuditReturns:
    def test_list_input(self):
        from quantproto.adapters import audit_returns
        r = _returns().tolist()
        report = audit_returns(r)
        _assert_report(report)

    def test_ndarray_input(self):
        from quantproto.adapters import audit_returns
        report = audit_returns(_returns())
        _assert_report(report)

    def test_series_input(self):
        from quantproto.adapters import audit_returns
        report = audit_returns(pd.Series(_returns()))
        _assert_report(report)

    def test_n_trials_passed_through(self):
        from quantproto.adapters import audit_returns
        r1 = audit_returns(_returns(), n_trials=1)
        r50 = audit_returns(_returns(), n_trials=50)
        # More trials → DSR is lower (multiple-testing penalty) → potentially
        # lower score; at minimum the statistics differ.
        assert r50["statistics"]["n_trials"] == 50

    def test_empty_raises(self):
        from quantproto.adapters import audit_returns
        with pytest.raises((ValueError, Exception)):
            audit_returns([])


# ── Backtrader adapter ───────────────────────────────────────────────────────

class _FakeAnalysis:
    """Mimics bt.analyzers.TimeReturn.get_analysis() result."""
    def __init__(self, rets):
        from datetime import date, timedelta
        start = date(2020, 1, 1)
        self._data = {
            start + timedelta(days=i): float(r) for i, r in enumerate(rets)
        }
    def get_analysis(self):
        return self._data


class _FakeAnalyzers:
    def __init__(self, rets):
        self.time_return = _FakeAnalysis(rets)

    def __dir__(self):
        return ["time_return"]

    def __getattr__(self, name):
        if name == "time_return":
            return object.__getattribute__(self, "time_return")
        raise AttributeError(name)


class _FakeStrategy:
    def __init__(self, rets):
        self.analyzers = _FakeAnalyzers(rets)
        self.data = [None] * len(rets)


class TestAuditBacktrader:
    def test_result_with_analyzer(self):
        from quantproto.adapters import audit_backtrader
        rets = _returns()
        result = [_FakeStrategy(rets)]
        report = audit_backtrader(result)
        _assert_report(report)

    def test_equity_kwarg_bypasses_result(self):
        from quantproto.adapters import audit_backtrader
        eq = _equity()
        report = audit_backtrader(None, equity=eq.tolist())
        _assert_report(report)

    def test_equity_as_series(self):
        from quantproto.adapters import audit_backtrader
        eq = pd.Series(_equity())
        report = audit_backtrader(None, equity=eq)
        _assert_report(report)

    def test_none_result_no_equity_raises(self):
        from quantproto.adapters import audit_backtrader
        with pytest.raises(ValueError, match="equity="):
            audit_backtrader(None)

    def test_bad_result_raises(self):
        from quantproto.adapters import audit_backtrader
        with pytest.raises(ValueError):
            audit_backtrader("not-a-list")

    def test_n_trials_forwarded(self):
        from quantproto.adapters import audit_backtrader
        result = [_FakeStrategy(_returns())]
        report = audit_backtrader(result, n_trials=20)
        assert report["statistics"]["n_trials"] == 20


# ── QuantConnect adapter ─────────────────────────────────────────────────────

def _qc_result(equity: np.ndarray | None = None) -> dict:
    """Build a minimal QC-style result dict."""
    if equity is None:
        equity = _equity()
    values = [{"x": i * 86400 * 1000, "y": float(v)} for i, v in enumerate(equity)]
    return {
        "Charts": {
            "Strategy Equity": {
                "Series": {
                    "Equity": {
                        "Values": values
                    }
                }
            }
        },
        "Statistics": {"Turnover": "50%"},
    }


class TestAuditQuantConnect:
    def test_qc_result_dict(self):
        from quantproto.adapters import audit_quantconnect
        report = audit_quantconnect(_qc_result())
        _assert_report(report)

    def test_equity_kwarg(self):
        from quantproto.adapters import audit_quantconnect
        report = audit_quantconnect(None, equity=_equity().tolist())
        _assert_report(report)

    def test_turnover_extracted_from_stats(self):
        from quantproto.adapters import audit_quantconnect
        result = _qc_result()
        result["Statistics"]["Turnover"] = "100%"
        report = audit_quantconnect(result)
        _assert_report(report)

    def test_missing_equity_raises(self):
        from quantproto.adapters import audit_quantconnect
        with pytest.raises(ValueError, match="equity curve"):
            audit_quantconnect({"Charts": {}})

    def test_none_result_no_equity_raises(self):
        from quantproto.adapters import audit_quantconnect
        with pytest.raises(ValueError, match="equity="):
            audit_quantconnect(None)

    def test_flat_equity_key(self):
        from quantproto.adapters import audit_quantconnect
        result = {"equity": _equity().tolist()}
        report = audit_quantconnect(result)
        _assert_report(report)

    def test_n_trials_forwarded(self):
        from quantproto.adapters import audit_quantconnect
        report = audit_quantconnect(_qc_result(), n_trials=30)
        assert report["statistics"]["n_trials"] == 30


# ── bt adapter ───────────────────────────────────────────────────────────────

class _FakeBtResult:
    def __init__(self, n: int = 300):
        eq = pd.Series(_equity(n), name="strategy_0")
        self.prices = pd.DataFrame({"strategy_0": eq})
        self.stats = pd.DataFrame({"strategy_0": {"turnover": 0.005}})


class TestAuditBt:
    def test_bt_result(self):
        from quantproto.adapters import audit_bt
        report = audit_bt(_FakeBtResult())
        _assert_report(report)

    def test_strategy_name_selection(self):
        from quantproto.adapters import audit_bt
        result = _FakeBtResult()
        report = audit_bt(result, strategy_name="strategy_0")
        _assert_report(report)

    def test_bad_strategy_name_raises(self):
        from quantproto.adapters import audit_bt
        with pytest.raises(ValueError, match="not found"):
            audit_bt(_FakeBtResult(), strategy_name="nonexistent")

    def test_no_prices_raises(self):
        from quantproto.adapters import audit_bt
        with pytest.raises((ValueError, AttributeError)):
            audit_bt("not-a-result")


# ── Zipline adapter ──────────────────────────────────────────────────────────

def _zipline_perf(n: int = 300, has_returns: bool = True) -> pd.DataFrame:
    """Minimal Zipline-style perf DataFrame."""
    r = _returns(n)
    eq = np.cumprod(1 + r) * 1_000_000
    df = pd.DataFrame({
        "portfolio_value": eq,
        "gross_leverage": np.ones(n) * 0.95,
    })
    if has_returns:
        df["returns"] = r
    return df


class TestAuditZipline:
    def test_with_returns_column(self):
        from quantproto.adapters import audit_zipline
        report = audit_zipline(_zipline_perf(has_returns=True))
        _assert_report(report)

    def test_fallback_to_portfolio_value(self):
        from quantproto.adapters import audit_zipline
        report = audit_zipline(_zipline_perf(has_returns=False))
        _assert_report(report)

    def test_non_dataframe_raises(self):
        from quantproto.adapters import audit_zipline
        with pytest.raises((ValueError, TypeError, Exception)):
            audit_zipline([1, 2, 3])

    def test_missing_columns_raises(self):
        from quantproto.adapters import audit_zipline
        with pytest.raises(ValueError, match="portfolio_value"):
            audit_zipline(pd.DataFrame({"something_else": [1, 2, 3]}))

    def test_n_trials_forwarded(self):
        from quantproto.adapters import audit_zipline
        report = audit_zipline(_zipline_perf(), n_trials=15)
        assert report["statistics"]["n_trials"] == 15
