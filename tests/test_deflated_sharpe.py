"""Tests for Deflated & Probabilistic Sharpe Ratio."""

import numpy as np
import pytest

from quantproto.integrity.deflated_sharpe import (
    probabilistic_sharpe_ratio,
    expected_max_sharpe,
    deflated_sharpe_ratio,
    minimum_track_record_length,
    analyze_returns,
)


class TestProbabilisticSharpe:
    def test_in_unit_interval(self):
        for sr in [-0.2, 0.0, 0.1, 0.5]:
            p = probabilistic_sharpe_ratio(sr, 252, 0.0, 3.0)
            assert 0.0 <= p <= 1.0

    def test_higher_sharpe_higher_psr(self):
        low = probabilistic_sharpe_ratio(0.05, 252)
        high = probabilistic_sharpe_ratio(0.20, 252)
        assert high > low

    def test_more_data_more_confidence(self):
        short = probabilistic_sharpe_ratio(0.1, 60)
        long = probabilistic_sharpe_ratio(0.1, 1000)
        assert long > short

    def test_zero_sharpe_is_half(self):
        assert probabilistic_sharpe_ratio(0.0, 252) == pytest.approx(0.5, abs=1e-9)

    def test_negative_skew_lowers_psr(self):
        # Negative skew inflates the variance term → lower confidence.
        base = probabilistic_sharpe_ratio(0.15, 252, skew=0.0)
        neg = probabilistic_sharpe_ratio(0.15, 252, skew=-1.0)
        assert neg < base


class TestExpectedMaxSharpe:
    def test_single_trial_is_zero(self):
        assert expected_max_sharpe(1, 0.5) == 0.0

    def test_increases_with_trials(self):
        a = expected_max_sharpe(10, 0.01)
        b = expected_max_sharpe(1000, 0.01)
        assert b > a > 0

    def test_zero_variance_zero(self):
        assert expected_max_sharpe(100, 0.0) == 0.0


class TestDeflatedSharpe:
    def test_dsr_leq_psr(self):
        # Deflating for multiple trials can only lower confidence.
        res = deflated_sharpe_ratio(0.15, 252, n_trials=50, var_sharpe=0.02)
        assert res["dsr"] <= res["psr_vs_zero"] + 1e-9

    def test_more_trials_lower_dsr(self):
        few = deflated_sharpe_ratio(0.15, 252, n_trials=5, var_sharpe=0.02)["dsr"]
        many = deflated_sharpe_ratio(0.15, 252, n_trials=500, var_sharpe=0.02)["dsr"]
        assert many <= few


class TestMinTRL:
    def test_inf_when_no_edge(self):
        assert minimum_track_record_length(0.0) == float("inf")
        assert minimum_track_record_length(-0.1) == float("inf")

    def test_positive_finite_with_edge(self):
        n = minimum_track_record_length(0.1)
        assert np.isfinite(n) and n > 1


class TestAnalyzeReturns:
    def test_keys_present(self):
        rng = np.random.RandomState(0)
        r = rng.normal(0.001, 0.01, 500)
        out = analyze_returns(r, n_trials=1)
        for k in ["sharpe_per_period", "psr", "min_track_record_length", "dsr"]:
            assert k in out

    def test_dsr_none_without_var(self):
        rng = np.random.RandomState(1)
        r = rng.normal(0.001, 0.01, 500)
        assert analyze_returns(r, n_trials=10, var_sharpe=None)["dsr"] is None

    def test_dsr_computed_with_var(self):
        rng = np.random.RandomState(2)
        r = rng.normal(0.001, 0.01, 500)
        assert analyze_returns(r, n_trials=10, var_sharpe=0.02)["dsr"] is not None
