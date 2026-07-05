"""Tests for the experiment tracker's API endpoints and MCP tool registration."""

import numpy as np
import pytest
from fastapi.testclient import TestClient


@pytest.fixture()
def client(tmp_path, monkeypatch):
    monkeypatch.setenv("QUANTPROTO_LEDGER", str(tmp_path / "ledger.db"))
    from quantproto.dashboard.api import app

    return TestClient(app)


def _log(client, name, returns, params):
    return client.post(
        f"/api/experiments/{name}/runs",
        json={"returns": list(returns), "params": params},
    )


class TestExperimentEndpoints:
    def test_log_and_status_roundtrip(self, client):
        rng = np.random.default_rng(0)
        for i in range(5):
            r = _log(client, "api-exp", rng.normal(0, 0.01, 200), {"lb": i})
            assert r.status_code == 200
        body = r.json()
        assert body["n_configs"] == 5
        assert body["budget_state"] in ("ok", "warning", "burned")

        detail = client.get("/api/experiments/api-exp").json()
        assert detail["status"]["n_runs"] == 5
        assert detail["chain_valid"] is True
        assert len(detail["runs"]) == 5
        assert "returns" not in detail["runs"][0]  # raw series not exposed

    def test_list_experiments(self, client):
        rng = np.random.default_rng(1)
        _log(client, "exp-a", rng.normal(0, 0.01, 100), {})
        names = [e["name"] for e in client.get("/api/experiments").json()["experiments"]]
        assert "exp-a" in names

    def test_equity_input(self, client):
        r = client.post(
            "/api/experiments/eq-exp/runs",
            json={"equity": [100, 101, 100.5, 102, 103], "params": {"x": 1}},
        )
        assert r.status_code == 200

    def test_requires_exactly_one_series(self, client):
        r = client.post("/api/experiments/bad/runs", json={"params": {}})
        assert r.status_code == 400
        r = client.post(
            "/api/experiments/bad/runs",
            json={"returns": [0.01, 0.02], "equity": [100, 101, 102], "params": {}},
        )
        assert r.status_code == 400

    def test_sensitivity_endpoint(self, client):
        rng = np.random.default_rng(2)
        for lb in (10, 20, 30, 40):
            _log(client, "sens-exp", rng.normal(0, 0.01, 200), {"lookback": lb})
        s = client.get("/api/experiments/sens-exp/sensitivity", params={"param": "lookback"}).json()
        assert s["param"] == "lookback"
        assert s["n_values"] == 4

    def test_report_endpoint(self, client):
        rng = np.random.default_rng(3)
        for i in range(9):
            _log(client, "rep-exp", rng.normal(0, 0.01, 256), {"lb": i})
        rep = client.get("/api/experiments/rep-exp/report").json()
        assert "score" in rep and "verdict" in rep
        assert rep["experiment"]["chain_valid"] is True
        assert rep["pbo"] is not None

    def test_report_404_when_empty(self, client):
        r = client.get("/api/experiments/nonexistent/report")
        assert r.status_code == 404

    def test_certificate_endpoint(self, client):
        rng = np.random.default_rng(20)
        for i in range(9):
            _log(client, "cert-exp", rng.normal(0, 0.01, 256), {"lb": i})
        r = client.get("/api/experiments/cert-exp/certificate")
        assert r.status_code == 200
        assert "text/html" in r.headers["content-type"]
        assert "cert-exp" in r.text

    def test_live_and_drift_endpoints(self, client):
        rng = np.random.default_rng(21)
        _log(client, "live-exp", rng.normal(0.001, 0.01, 500), {"a": 1})
        r = client.post(
            "/api/experiments/live-exp/live",
            json={"returns": list(rng.normal(0.001, 0.01, 60)), "params": {"a": 1}},
        )
        assert r.status_code == 200
        assert r.json()["drift"]["state"] in ("consistent", "watch", "diverging")

        d = client.get("/api/experiments/live-exp/drift").json()
        assert d["state"] in ("consistent", "watch", "diverging")

    def test_drift_no_data_states(self, client):
        d = client.get("/api/experiments/never-seen/drift").json()
        assert d["state"] == "no_backtest"


class TestMCPTools:
    def test_tracker_tools_registered(self):
        import asyncio
        from quantproto.mcp.server import mcp

        tools = asyncio.run(mcp.list_tools())
        names = {t.name for t in tools}
        assert {"log_run", "research_budget", "experiment_report",
                "log_live", "live_drift"} <= names

    def test_log_run_and_budget_flow(self, tmp_path, monkeypatch):
        monkeypatch.setenv("QUANTPROTO_LEDGER", str(tmp_path / "mcp.db"))
        from quantproto.mcp import server

        rng = np.random.default_rng(4)
        out = server.log_run(
            experiment="mcp-exp",
            returns=list(rng.normal(0, 0.01, 200)),
            params={"lookback": 20},
        )
        assert out["n_configs"] == 1
        assert "receipt" in out

        budget = server.research_budget(experiment="mcp-exp")
        assert budget["n_runs"] == 1

    def test_log_live_and_live_drift(self, tmp_path, monkeypatch):
        monkeypatch.setenv("QUANTPROTO_LEDGER", str(tmp_path / "mcp_live.db"))
        from quantproto.mcp import server

        rng = np.random.default_rng(5)
        server.log_run(experiment="mcp-live", returns=list(rng.normal(0.001, 0.01, 400)),
                        params={"a": 1})
        out = server.log_live(experiment="mcp-live",
                               returns=list(rng.normal(0.001, 0.01, 60)), params={"a": 1})
        assert "drift" in out
        d = server.live_drift(experiment="mcp-live")
        assert d["state"] in ("consistent", "watch", "diverging")
