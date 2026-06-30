"""Tests for Probability of Backtest Overfitting (CSCV)."""

import numpy as np
import pytest

from quantproto.integrity.pbo import pbo_cscv


class TestPBOContract:
    def test_requires_two_configs(self):
        with pytest.raises(ValueError):
            pbo_cscv(np.random.RandomState(0).normal(size=(200, 1)))

    def test_even_splits_only(self):
        with pytest.raises(ValueError):
            pbo_cscv(np.random.RandomState(0).normal(size=(200, 5)), n_splits=7)

    def test_output_keys_and_bounds(self):
        m = np.random.RandomState(0).normal(size=(320, 8))
        out = pbo_cscv(m, n_splits=8)
        for k in ["pbo", "logits", "oos_degradation", "prob_oos_loss", "n_configs"]:
            assert k in out
        assert 0.0 <= out["pbo"] <= 1.0
        assert 0.0 <= out["prob_oos_loss"] <= 1.0


class TestPBODiscrimination:
    def test_pure_noise_is_overfit(self):
        # All configs are independent noise → the IS-best is luck → PBO high.
        m = np.random.RandomState(42).normal(0, 0.01, size=(480, 12))
        out = pbo_cscv(m, n_splits=12)
        assert out["pbo"] > 0.4

    def test_genuine_edge_low_pbo(self):
        # One config has a persistent real edge; it should generalise OOS.
        rng = np.random.RandomState(7)
        T, N = 480, 12
        m = rng.normal(0, 0.01, size=(T, N))
        # Config 0 gets a strong, persistent positive drift across all blocks.
        m[:, 0] += 0.006
        out = pbo_cscv(m, n_splits=12)
        assert out["pbo"] < 0.25

    def test_noise_degradation_positive(self):
        m = np.random.RandomState(1).normal(0, 0.01, size=(480, 12))
        out = pbo_cscv(m, n_splits=12)
        # IS-selected winner degrades OOS on pure noise.
        assert out["oos_degradation"] > 0
