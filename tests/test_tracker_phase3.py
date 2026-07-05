"""Tests for phase-3 tracker features: Postgres fallback, live-drift monitor,
provenance certificate rendering, and deeper framework capture hooks.
"""

import numpy as np
import pandas as pd
import pytest

from quantproto.tracker import Experiment, RunLedger
from quantproto.tracker.drift import live_consistency, MIN_LIVE_OBS
from quantproto.tracker.certificate import render_certificate_html


def _noise(rng, n=300, mu=0.0, sigma=0.01):
    return rng.normal(mu, sigma, n)


@pytest.fixture()
def ledger(tmp_path):
    lg = RunLedger(tmp_path / "p3.db")
    yield lg
    lg.close()


@pytest.fixture()
def exp(ledger):
    return Experiment("p3-exp", ledger=ledger)


class TestPostgresFallback:
    def test_bad_database_url_falls_back_to_sqlite(self, tmp_path, monkeypatch):
        monkeypatch.setenv("QUANTPROTO_LEDGER", str(tmp_path / "fallback.db"))
        lg = RunLedger(url="postgresql://nonexistent-host-xyz:5432/db")
        assert lg.backend == "sqlite"
        lg.record_run("e1", np.array([0.01, 0.02, -0.01]), {"a": 1})
        assert lg.verify_chain("e1")
        lg.close()

    def test_sqlite_default_backend(self, ledger):
        assert ledger.backend == "sqlite"


class TestLiveDrift:
    def test_no_backtest_yet(self, exp):
        assert exp.drift()["state"] == "no_backtest"

    def test_no_live_data_yet(self, exp):
        rng = np.random.default_rng(0)
        exp.log(_noise(rng), params={"a": 1})
        assert exp.drift()["state"] == "no_live_data"

    def test_insufficient_live_obs(self, exp):
        rng = np.random.default_rng(1)
        exp.log(_noise(rng), params={"a": 1})
        exp.log_live(_noise(rng, n=5), params={"a": 1})
        d = exp.drift()
        assert d["state"] == "insufficient_data"

    def test_consistent_when_live_matches_backtest(self, exp):
        rng = np.random.default_rng(2)
        exp.log(rng.normal(0.001, 0.01, 500), params={"a": 1})
        exp.log_live(rng.normal(0.001, 0.01, 100), params={"a": 1})
        d = exp.drift()
        assert d["state"] in ("consistent", "watch")

    def test_diverging_when_live_decays(self, exp):
        rng = np.random.default_rng(3)
        exp.log(rng.normal(0.004, 0.005, 800), params={"a": 1})  # strong backtest edge
        exp.log_live(rng.normal(-0.002, 0.02, 60), params={"a": 1})  # live is losing
        d = exp.drift()
        assert d["state"] == "diverging"

    def test_live_runs_excluded_from_config_search(self, exp):
        rng = np.random.default_rng(4)
        exp.log(_noise(rng), params={"a": 1})
        exp.log_live(_noise(rng, n=50), params={"a": 1})  # same params_hash as backtest
        status = exp.status()
        assert status["n_configs"] == 1  # live run must not overwrite/inflate config pool

    def test_live_consistency_function_directly(self):
        rng = np.random.default_rng(5)
        bt = rng.normal(0.002, 0.01, 500)
        live = rng.normal(0.002, 0.01, 100)
        res = live_consistency(bt, live)
        assert res["n_live"] == 100
        assert 0.0 <= res["consistency_prob"] <= 1.0

    def test_min_live_obs_boundary(self):
        rng = np.random.default_rng(6)
        bt = rng.normal(0.001, 0.01, 300)
        live = rng.normal(0.001, 0.01, MIN_LIVE_OBS - 1)
        assert live_consistency(bt, live)["state"] == "insufficient_data"


class TestCertificate:
    def test_renders_self_contained_html(self, exp):
        rng = np.random.default_rng(7)
        for i in range(10):
            exp.log(_noise(rng, 256), params={"lookback": i})
        report = exp.report()
        html = render_certificate_html(report)
        assert "<!doctype html>" in html.lower()
        assert "p3-exp" in html
        assert "Chain intact" in html
        assert str(report["score"]) in html or f"{report['score']:.1f}" in html

    def test_broken_chain_shows_warning(self, exp):
        rng = np.random.default_rng(8)
        for i in range(9):
            exp.log(_noise(rng, 256), params={"lookback": i})
        report = exp.report()
        assert report["experiment"]["chain_valid"] is True
        report["experiment"]["chain_valid"] = False  # simulate a detected tamper
        html = render_certificate_html(report)
        assert "CHAIN BROKEN" in html


class TestFrameworkCaptureHooks:
    def test_capture_zipline(self, exp):
        rng = np.random.default_rng(9)
        perf = pd.DataFrame({"returns": rng.normal(0, 0.01, 200)})
        receipt = exp.capture_zipline(perf, params={"lookback": 10})
        assert "id" in receipt
        assert exp.runs()[-1]["source"] == "zipline"

    def test_capture_bt(self, exp):
        rng = np.random.default_rng(10)

        class FakeResult:
            prices = pd.DataFrame({"strat": 100 * np.cumprod(1 + rng.normal(0, 0.01, 200))})
            stats = pd.DataFrame()

        receipt = exp.capture_bt(FakeResult(), params={"lookback": 20})
        assert "id" in receipt
        assert exp.runs()[-1]["source"] == "bt"
