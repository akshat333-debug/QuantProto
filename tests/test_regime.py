"""Tests for RegimeHMM — Phase E validation."""

import numpy as np
import pandas as pd
import pytest

from quantproto.regime_model import RegimeHMM


@pytest.fixture
def regime_model():
    return RegimeHMM(n_states=3, seed=42)


@pytest.fixture
def returns_series():
    """Synthetic return series with regime-like structure."""
    np.random.seed(42)
    # Bull phase (100 days, positive drift)
    bull = np.random.normal(0.002, 0.008, 100)
    # Bear phase (80 days, negative drift, high vol)
    bear = np.random.normal(-0.003, 0.025, 80)
    # Neutral (120 days, flat)
    neutral = np.random.normal(0.0, 0.012, 120)
    returns = np.concatenate([bull, bear, neutral])
    dates = pd.bdate_range("2022-01-01", periods=len(returns))
    return pd.Series(returns, index=dates, name="returns")


@pytest.fixture
def features(returns_series):
    return RegimeHMM.engineer_features(returns_series, window=20)


@pytest.fixture
def fitted_model(regime_model, features):
    regime_model.fit(features)
    return regime_model


# ── Feature engineering ────────────────────────────────────────────

class TestEngineerFeatures:
    def test_columns(self, features):
        assert list(features.columns) == ["mean", "volatility", "skewness"]

    def test_no_nans(self, features):
        assert not features.isna().any().any()

    def test_length_reduced_by_window(self, returns_series):
        window = 20
        feat = RegimeHMM.engineer_features(returns_series, window=window)
        assert len(feat) == len(returns_series) - window + 1

    def test_accepts_dataframe(self):
        np.random.seed(42)
        df = pd.DataFrame(
            np.random.normal(0, 0.01, (100, 3)),
            columns=["A", "B", "C"],
        )
        feat = RegimeHMM.engineer_features(df, window=10)
        assert len(feat) > 0


# ── Model fitting ──────────────────────────────────────────────────

class TestFit:
    def test_returns_self(self, regime_model, features):
        result = regime_model.fit(features)
        assert result is regime_model

    def test_model_is_set(self, fitted_model):
        assert fitted_model._model is not None

    def test_state_labels_assigned(self, fitted_model):
        assert fitted_model._state_label_map is not None
        assert set(fitted_model._state_label_map.values()) == {"BULL", "NEUTRAL", "BEAR"}


# ── Prediction ─────────────────────────────────────────────────────

class TestPredictStates:
    def test_output_has_valid_labels(self, fitted_model, features):
        states = fitted_model.predict_states(features)
        valid_labels = {"BULL", "NEUTRAL", "BEAR"}
        assert set(states.unique()).issubset(valid_labels)

    def test_output_length(self, fitted_model, features):
        states = fitted_model.predict_states(features)
        assert len(states) == len(features)

    def test_output_index(self, fitted_model, features):
        states = fitted_model.predict_states(features)
        pd.testing.assert_index_equal(states.index, features.index)

    def test_unfitted_raises(self, features):
        model = RegimeHMM()
        with pytest.raises(RuntimeError, match="not fitted"):
            model.predict_states(features)


# ── Posterior confidence ───────────────────────────────────────────

class TestPosteriorConfidence:
    def test_in_valid_range(self, fitted_model, features):
        conf = fitted_model.posterior_confidence(features)
        assert (conf >= 1 / 3 - 0.01).all(), "Confidence below floor"
        assert (conf <= 1.0 + 1e-10).all(), "Confidence above 1"

    def test_length(self, fitted_model, features):
        conf = fitted_model.posterior_confidence(features)
        assert len(conf) == len(features)


# ── Exposure adjustment ───────────────────────────────────────────

class TestAdjustExposure:
    def test_bear_reduces_exposure(self, fitted_model, features):
        """BEAR regime should reduce signal vs. BULL."""
        states = fitted_model.predict_states(features)
        signal = pd.Series(np.ones(len(features)), index=features.index)

        adjusted = RegimeHMM.adjust_exposure(signal, states)

        bear_mask = states == "BEAR"
        bull_mask = states == "BULL"

        if bear_mask.any() and bull_mask.any():
            assert adjusted[bear_mask].mean() < adjusted[bull_mask].mean()

    def test_output_length(self, fitted_model, features):
        states = fitted_model.predict_states(features)
        signal = pd.Series(np.ones(len(features)), index=features.index)
        adjusted = RegimeHMM.adjust_exposure(signal, states)
        assert len(adjusted) == len(features)

    def test_deterministic(self, fitted_model, features):
        states = fitted_model.predict_states(features)
        signal = pd.Series(np.ones(len(features)), index=features.index)
        a1 = RegimeHMM.adjust_exposure(signal, states)
        a2 = RegimeHMM.adjust_exposure(signal, states)
        pd.testing.assert_series_equal(a1, a2)

    def test_dataframe_input(self, fitted_model, features):
        states = fitted_model.predict_states(features)
        signal_df = pd.DataFrame(
            np.ones((len(features), 3)),
            index=features.index,
            columns=["A", "B", "C"],
        )
        adjusted = RegimeHMM.adjust_exposure(signal_df, states)
        assert adjusted.shape == signal_df.shape
