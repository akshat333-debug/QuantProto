"""Tests for bring-your-own-backtest ingestion."""

import numpy as np
import pytest

from quantproto.integrity.ingest import (
    parse_returns,
    equity_to_returns,
    trades_to_returns,
    parse_csv,
    parse_variant_matrix,
)


class TestParseReturns:
    def test_basic(self):
        r = parse_returns([0.01, -0.02, 0.005])
        assert r.shape == (3,)

    def test_rejects_non_numeric(self):
        with pytest.raises(ValueError):
            parse_returns([0.01, "abc", 0.02])

    def test_rejects_empty(self):
        with pytest.raises(ValueError):
            parse_returns([])


class TestEquity:
    def test_converts_to_returns(self):
        r = equity_to_returns([100, 110, 99])
        assert r == pytest.approx([0.1, -0.1], rel=1e-6)

    def test_rejects_nonpositive(self):
        with pytest.raises(ValueError):
            equity_to_returns([100, 0, 90])

    def test_needs_two_points(self):
        with pytest.raises(ValueError):
            equity_to_returns([100])


class TestTrades:
    def test_fractional_passthrough(self):
        r = trades_to_returns([0.02, -0.01])
        assert r == pytest.approx([0.02, -0.01])

    def test_with_capital(self):
        r = trades_to_returns([200, -100], capital=10000)
        assert r == pytest.approx([0.02, -0.01])


class TestCSV:
    def test_single_column_no_header(self):
        cols = parse_csv("0.01\n-0.02\n0.03")
        assert len(cols) == 1
        vals = list(cols.values())[0]
        assert vals.shape == (3,)

    def test_multi_column_with_header(self):
        cols = parse_csv("a,b\n0.01,0.02\n-0.01,0.03")
        assert set(cols.keys()) == {"a", "b"}
        assert cols["a"].shape == (2,)

    def test_variant_matrix_from_csv(self):
        m = parse_variant_matrix("s1,s2\n0.01,0.02\n-0.01,0.03\n0.0,0.01")
        assert m.shape == (3, 2)

    def test_variant_matrix_from_list(self):
        m = parse_variant_matrix([[0.01, 0.02], [-0.01, 0.03]])
        assert m.shape == (2, 2)

    def test_variant_matrix_rejects_1d(self):
        with pytest.raises(ValueError):
            parse_variant_matrix([0.01, 0.02, 0.03])
