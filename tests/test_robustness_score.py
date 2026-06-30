"""Tests for the aggregate Robustness Score and bias checks."""

import numpy as np
import pytest

from quantproto.integrity.score import robustness_report
from quantproto.integrity.bias_checks import detect_red_flags, integrity_checklist


class TestRobustnessReport:
    def test_score_in_range_and_keys(self):
        r = np.random.RandomState(0).normal(0.0005, 0.01, 500)
        rep = robustness_report(r, n_trials=1, turnover=0.5)
        assert 0.0 <= rep["score"] <= 100.0
        for k in ["score", "verdict", "components", "statistics", "red_flags", "checklist"]:
            assert k in rep
        assert rep["verdict"] in {"robust", "fragile", "likely_overfit"}

    def test_strong_clean_edge_scores_higher_than_noise(self):
        rng = np.random.RandomState(1)
        strong = rng.normal(0.0015, 0.008, 1000)   # solid Sharpe, long sample
        noise = rng.normal(0.0, 0.02, 90)           # no edge, short sample
        s_strong = robustness_report(strong, turnover=0.2)["score"]
        s_noise = robustness_report(noise, turnover=2.0)["score"]
        assert s_strong > s_noise

    def test_short_sample_flagged(self):
        r = np.random.RandomState(2).normal(0.001, 0.01, 30)
        rep = robustness_report(r)
        codes = {f["code"] for f in rep["red_flags"]}
        assert "short_sample" in codes

    def test_variant_matrix_adds_pbo(self):
        rng = np.random.RandomState(3)
        vm = rng.normal(0, 0.01, size=(480, 10))
        chosen = vm[:, 0]
        rep = robustness_report(chosen, variant_matrix=vm, n_splits=10)
        assert rep["pbo"] is not None
        assert 0.0 <= rep["pbo"]["pbo"] <= 1.0

    def test_note_when_selection_unassessed(self):
        r = np.random.RandomState(4).normal(0.001, 0.01, 500)
        rep = robustness_report(r, n_trials=1)
        assert any("Selection-bias" in n for n in rep["notes"])


class TestBiasChecks:
    def test_implausible_sharpe_flagged(self):
        # Near-constant positive returns → astronomically high Sharpe.
        r = np.full(300, 0.01) + np.random.RandomState(0).normal(0, 1e-5, 300)
        codes = {f["code"] for f in detect_red_flags(r)}
        assert "implausible_sharpe" in codes or "smooth_equity" in codes

    def test_clean_returns_few_flags(self):
        r = np.random.RandomState(5).normal(0.0003, 0.012, 800)
        flags = detect_red_flags(r)
        assert all(f["severity"] != "high" for f in flags)

    def test_checklist_has_known_biases(self):
        codes = {c["code"] for c in integrity_checklist()}
        assert {"survivorship", "lookahead", "costs"}.issubset(codes)
