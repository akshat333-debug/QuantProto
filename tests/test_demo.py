"""Tests for Demo CLI — Phase H validation."""

from __future__ import annotations

import json
import os
import tempfile

import numpy as np
import pandas as pd
import pytest

from quantproto.demo.data_loader import load_universe, generate_prices
from quantproto.demo.run_demo import run_demo, hash_file


# ── Data loader (H1) ─────────────────────────────────────────────────

class TestDataLoader:
    def test_default_universe(self):
        universe = load_universe()
        assert len(universe) == 5
        assert "AAPL" in universe

    def test_custom_universe(self):
        universe = load_universe(["X", "Y"])
        assert universe == ["X", "Y"]

    def test_generate_prices_shape(self):
        prices = generate_prices(["A", "B", "C"], n_days=100, seed=42)
        assert isinstance(prices, pd.DataFrame)
        assert prices.shape == (100, 3)

    def test_generate_prices_deterministic(self):
        p1 = generate_prices(["A"], n_days=50, seed=42)
        p2 = generate_prices(["A"], n_days=50, seed=42)
        pd.testing.assert_frame_equal(p1, p2)

    def test_prices_positive(self):
        prices = generate_prices(["A", "B"], n_days=200, seed=42)
        assert (prices > 0).all().all()


# ── Demo pipeline (H2, H3, H4) ───────────────────────────────────────

class TestRunDemo:
    @pytest.fixture
    def demo_output(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            result = run_demo(seed=42, output_dir=tmpdir)
            result["output_dir"] = tmpdir
            yield result

    def test_backtest_json_exists(self, demo_output):
        assert os.path.exists(demo_output["backtest_path"])

    def test_equity_curve_exists(self, demo_output):
        assert os.path.exists(demo_output["equity_path"])

    def test_manifest_exists(self, demo_output):
        assert os.path.exists(demo_output["manifest_path"])

    def test_backtest_json_valid(self, demo_output):
        with open(demo_output["backtest_path"]) as f:
            data = json.load(f)
        assert "seed" in data
        assert "action" in data
        assert "bootstrap_ci" in data
        assert "risk_report" in data

    def test_manifest_has_hashes(self, demo_output):
        with open(demo_output["manifest_path"]) as f:
            manifest = json.load(f)
        assert "files" in manifest
        assert "backtest.json" in manifest["files"]
        assert "equity_curve.png" in manifest["files"]
        # Hashes are 64-char hex strings
        for fname, h in manifest["files"].items():
            assert len(h) == 64

    def test_equity_curve_is_valid_png(self, demo_output):
        with open(demo_output["equity_path"], "rb") as f:
            header = f.read(8)
        # PNG magic bytes
        assert header[:4] == b"\x89PNG"

    def test_deterministic_output(self):
        """Two runs with same seed → identical backtest.json content."""
        with tempfile.TemporaryDirectory() as dir1, tempfile.TemporaryDirectory() as dir2:
            run_demo(seed=42, output_dir=dir1)
            run_demo(seed=42, output_dir=dir2)

            with open(os.path.join(dir1, "backtest.json")) as f1:
                data1 = json.load(f1)
            with open(os.path.join(dir2, "backtest.json")) as f2:
                data2 = json.load(f2)

            assert data1 == data2
