"""Tests for the experiment tracker: ledger chain, budget math, API surface."""

import numpy as np
import pytest

from quantproto.tracker import Experiment, RunLedger
from quantproto.tracker.budget import research_budget, parameter_sensitivity


@pytest.fixture()
def ledger(tmp_path):
    lg = RunLedger(tmp_path / "test.db")
    yield lg
    lg.close()


@pytest.fixture()
def exp(ledger):
    return Experiment("test-exp", ledger=ledger)


def _noise(rng, n=300, mu=0.0):
    return rng.normal(mu, 0.01, n)


class TestLedger:
    def test_record_and_list(self, ledger):
        rng = np.random.default_rng(0)
        receipt = ledger.record_run("e1", _noise(rng), {"a": 1})
        assert receipt["seq"] == 1
        runs = ledger.list_runs("e1", with_returns=True)
        assert len(runs) == 1
        assert runs[0]["params"] == {"a": 1}
        assert runs[0]["n_obs"] == 300
        assert isinstance(runs[0]["returns"], np.ndarray)

    def test_chain_verifies_and_detects_tampering(self, ledger):
        rng = np.random.default_rng(1)
        for i in range(5):
            ledger.record_run("e1", _noise(rng), {"a": i})
        assert ledger.verify_chain("e1")
        # Tamper with a mid-chain row's returns.
        ledger._conn.execute(
            "UPDATE runs SET returns = ? WHERE experiment = 'e1' AND seq = 3",
            ("[0.5, 0.5, 0.5]",),
        )
        ledger._conn.commit()
        assert not ledger.verify_chain("e1")

    def test_chains_are_per_experiment(self, ledger):
        rng = np.random.default_rng(2)
        ledger.record_run("e1", _noise(rng), {})
        ledger.record_run("e2", _noise(rng), {})
        assert ledger.verify_chain("e1")
        assert ledger.verify_chain("e2")

    def test_rejects_bad_returns(self, ledger):
        with pytest.raises(ValueError):
            ledger.record_run("e1", np.array([0.01]), {})
        with pytest.raises(ValueError):
            ledger.record_run("e1", np.array([0.01, np.nan]), {})


class TestBudget:
    def test_empty(self):
        assert research_budget([])["budget_state"] == "empty"

    def test_noise_search_gets_burned_or_warned(self, exp):
        """Best-of-40 pure-noise configs must not read as a real edge."""
        rng = np.random.default_rng(3)
        for i in range(40):
            exp.log(_noise(rng, 250), params={"lookback": i})
        s = exp.status()
        assert s["n_configs"] == 40
        assert s["budget_state"] in ("burned", "warning")
        assert s["spurious_sharpe_ann"] > 0
        assert s["dsr"] is None or s["dsr"] < 0.95

    def test_real_edge_survives(self, exp):
        """A genuinely strong edge with few trials should score ok."""
        rng = np.random.default_rng(4)
        exp.log(rng.normal(0.002, 0.01, 1000), params={"lookback": 20})
        exp.log(rng.normal(0.0019, 0.01, 1000), params={"lookback": 30})
        s = exp.status()
        assert s["budget_state"] == "ok"
        assert s["best_sharpe_ann"] > s["spurious_sharpe_ann"]

    def test_duplicate_configs_count_once(self, exp):
        rng = np.random.default_rng(5)
        for _ in range(3):
            exp.log(_noise(rng), params={"lookback": 20})
        s = exp.status()
        assert s["n_runs"] == 3
        assert s["n_configs"] == 1

    def test_pbo_appears_with_enough_configs(self, exp):
        rng = np.random.default_rng(6)
        for i in range(10):
            exp.log(_noise(rng, 256), params={"lookback": i})
        s = exp.status()
        assert s["pbo"] is not None
        assert 0.0 <= s["pbo"]["pbo"] <= 1.0


class TestSensitivity:
    def test_sharp_peak_flagged(self, exp):
        rng = np.random.default_rng(7)
        for lb in (10, 20, 30, 40, 50):
            mu = 0.003 if lb == 30 else 0.0  # only lookback=30 "works"
            exp.log(rng.normal(mu, 0.01, 400), params={"lookback": lb})
        s = exp.sensitivity("lookback")
        assert s["peak_value"] == 30
        assert s["verdict"] in ("sharp_peak", "soft_peak")

    def test_plateau_ok(self, exp):
        rng = np.random.default_rng(8)
        for lb in (10, 20, 30, 40, 50):
            exp.log(rng.normal(0.002, 0.01, 400), params={"lookback": lb})
        s = exp.sensitivity("lookback")
        assert s["verdict"] == "plateau"

    def test_insufficient_values(self, exp):
        rng = np.random.default_rng(9)
        exp.log(_noise(rng), params={"lookback": 10})
        s = exp.sensitivity("lookback")
        assert s["verdict"] == "insufficient"


class TestExperimentAPI:
    def test_context_manager_logs(self, exp):
        rng = np.random.default_rng(10)
        with exp.run(params={"a": 1}) as run:
            run.log_returns(_noise(rng))
        assert run.result is not None
        assert exp.status()["n_runs"] == 1

    def test_context_manager_requires_logging(self, exp):
        with pytest.raises(RuntimeError, match="without logging"):
            with exp.run(params={"a": 1}):
                pass

    def test_context_manager_skips_on_error(self, exp):
        with pytest.raises(ZeroDivisionError):
            with exp.run(params={"a": 1}):
                _ = 1 / 0
        assert exp.status()["budget_state"] == "empty"

    def test_log_equity(self, exp):
        equity = [100.0, 101.0, 100.5, 102.0, 103.1]
        with exp.run(params={}) as run:
            run.log_equity(equity)
        runs = exp.runs()
        assert runs[0]["n_obs"] == 4  # equity → returns loses one obs

    def test_log_trades(self, exp):
        with exp.run(params={}) as run:
            run.log_trades([50.0, -20.0, 30.0], capital=10_000)
        assert exp.runs()[0]["n_obs"] == 3

    def test_report_includes_experiment_block(self, exp):
        rng = np.random.default_rng(11)
        for i in range(10):
            exp.log(_noise(rng, 256), params={"lookback": i})
        rep = exp.report()
        assert rep["experiment"]["n_configs"] == 10
        assert rep["experiment"]["chain_valid"] is True
        assert rep["pbo"] is not None  # variant matrix auto-built
        assert "score" in rep and "verdict" in rep

    def test_strategy_code_hash_recorded(self, exp):
        def my_strategy():
            return 42

        rng = np.random.default_rng(12)
        exp.log(_noise(rng), params={}, strategy=my_strategy)
        assert exp.runs()[0]["code_hash"] is not None

    def test_top_level_factory(self, tmp_path):
        import quantproto as qp

        e = qp.experiment("factory-test", ledger_path=str(tmp_path / "l.db"))
        rng = np.random.default_rng(13)
        e.log(_noise(rng), params={"x": 1})
        assert e.status()["n_runs"] == 1


class TestCLI:
    def test_status_and_verify(self, tmp_path, capsys):
        from quantproto.tracker.cli import main

        db = str(tmp_path / "cli.db")
        lg = RunLedger(db)
        e = Experiment("cli-exp", ledger=lg)
        rng = np.random.default_rng(14)
        for i in range(5):
            e.log(_noise(rng), params={"lookback": i * 10})
        lg.close()

        assert main(["--ledger", db, "list"]) == 0
        assert "cli-exp" in capsys.readouterr().out
        assert main(["--ledger", db, "status", "cli-exp"]) == 0
        out = capsys.readouterr().out
        assert "runs / configs" in out
        assert main(["--ledger", db, "verify", "cli-exp"]) == 0
        assert "VALID" in capsys.readouterr().out
