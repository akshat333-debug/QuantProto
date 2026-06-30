"""Tests for Real Data Pipeline + Universe (T1.4)."""

import numpy as np
import pandas as pd
import pytest

from quantproto.data.fetcher import fetch_prices, _generate_synthetic
from quantproto.data.universe import UniverseManager


class TestSyntheticFallback:
    def test_returns_dataframe(self):
        df = _generate_synthetic(["A", "B"], "2023-01-01", "2023-06-01")
        assert isinstance(df, pd.DataFrame)
        assert df.shape[1] == 2

    def test_positive_prices(self):
        df = _generate_synthetic(["X"], "2023-01-01", "2023-12-31")
        assert (df > 0).all().all()

    def test_deterministic(self):
        d1 = _generate_synthetic(["A"], "2023-01-01", "2023-06-01")
        d2 = _generate_synthetic(["A"], "2023-01-01", "2023-06-01")
        pd.testing.assert_frame_equal(d1, d2)


class TestFetchPrices:
    def test_opt_in_synthetic_fallback(self):
        # With explicit opt-in, an unfetchable ticker falls back to synthetic.
        df = fetch_prices(
            ["FAKE_TICKER_XYZ"], start="2023-01-01", end="2023-03-01",
            cache=False, allow_synthetic_fallback=True,
        )
        assert isinstance(df, pd.DataFrame)
        assert df.shape[1] >= 1

    def test_fails_loud_without_optin(self):
        # Default: never silently fabricate data when live fetch is impossible.
        from quantproto.data.fetcher import LiveDataError
        with pytest.raises(LiveDataError):
            fetch_prices(
                ["FAKE_TICKER_XYZ"], start="2023-01-01", end="2023-03-01",
                cache=False,
            )


class TestUniverseManager:
    def test_default_universe(self):
        um = UniverseManager()
        assert len(um.get_universe()) == 10

    def test_custom_universe(self):
        um = UniverseManager(["A", "B", "C"])
        assert um.get_universe() == ["A", "B", "C"]

    def test_add_remove(self):
        um = UniverseManager(["A", "B"])
        um.add("C")
        assert "C" in um.get_universe()
        um.remove("A")
        assert "A" not in um.get_universe()

    def test_filter_by_availability(self):
        np.random.seed(42)
        prices = pd.DataFrame({
            "A": np.random.randn(100),
            "B": [np.nan] * 50 + list(np.random.randn(50)),
        })
        um = UniverseManager(["A", "B"])
        available = um.filter_by_data_availability(prices, min_pct=0.9)
        assert "A" in available
        assert "B" not in available

    def test_to_dict(self):
        um = UniverseManager(["X", "Y"])
        d = um.to_dict()
        assert d["count"] == 2
