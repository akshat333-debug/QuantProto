"""Tests for Agents — Phase G validation."""

from __future__ import annotations

import time

import jwt as pyjwt
import numpy as np
import pandas as pd
import pytest
from fastapi.testclient import TestClient

from quantproto.agents.auth import sign_token, verify_token, DEFAULT_SECRET
from quantproto.agents.agent_card import AgentCard
from quantproto.agents.alpha_agent import AlphaAgent
from quantproto.agents.risk_agent import RiskAgent
from quantproto.agents.orchestrator import Orchestrator
from quantproto.agents.http_server import app


# ── Fixtures ──────────────────────────────────────────────────────────

@pytest.fixture
def sample_prices():
    np.random.seed(42)
    tickers = ["A", "B", "C"]
    dates = pd.bdate_range("2023-01-01", periods=200)
    data = {}
    for t in tickers:
        data[t] = 100 * np.exp(np.cumsum(np.random.normal(0.0005, 0.02, 200)))
    return pd.DataFrame(data, index=dates)


@pytest.fixture
def valid_token():
    return sign_token("test-agent")


@pytest.fixture
def client():
    return TestClient(app)


# ── JWT Auth (G4) ─────────────────────────────────────────────────────

class TestJWTAuth:
    def test_sign_verify_roundtrip(self):
        token = sign_token("alpha-agent")
        payload = verify_token(token)
        assert payload["agent_id"] == "alpha-agent"
        assert "iat" in payload
        assert "exp" in payload

    def test_expired_token_rejected(self):
        token = sign_token("agent", expiry_seconds=0)
        time.sleep(0.1)
        with pytest.raises(pyjwt.ExpiredSignatureError):
            verify_token(token)

    def test_invalid_signature_rejected(self):
        token = sign_token("agent", secret="correct-secret")
        with pytest.raises(pyjwt.InvalidSignatureError):
            verify_token(token, secret="wrong-secret")

    def test_malformed_token(self):
        with pytest.raises(pyjwt.DecodeError):
            verify_token("not.a.valid.token")


# ── Agent Card (G5) ──────────────────────────────────────────────────

class TestAgentCard:
    def test_to_json_valid(self):
        card = AgentCard(
            name="AlphaAgent",
            description="Generates alpha signals",
            capabilities=["alpha_generation"],
            endpoint="http://localhost:8000/tasks",
        )
        json_str = card.to_json()
        import json
        data = json.loads(json_str)
        assert data["name"] == "AlphaAgent"
        assert "capabilities" in data
        assert "endpoint" in data
        assert "auth_scheme" in data

    def test_roundtrip(self):
        card = AgentCard(
            name="Test",
            description="Test agent",
            capabilities=["test"],
            endpoint="/test",
        )
        restored = AgentCard.from_json(card.to_json())
        assert restored.name == card.name
        assert restored.capabilities == card.capabilities

    def test_required_fields_in_dict(self):
        card = AgentCard(
            name="A",
            description="B",
            capabilities=["c"],
            endpoint="/d",
        )
        d = card.to_dict()
        required = {"name", "description", "capabilities", "endpoint", "auth_scheme", "version"}
        assert required.issubset(set(d.keys()))


# ── Alpha Agent (G1) ─────────────────────────────────────────────────

class TestAlphaAgent:
    def test_produces_valid_signal(self, sample_prices):
        agent = AlphaAgent(lookback=20)
        result = agent.generate_signal(sample_prices)
        assert "signal" in result
        assert "metadata" in result
        assert set(result["signal"].keys()) == set(sample_prices.columns)

    def test_metadata_fields(self, sample_prices):
        agent = AlphaAgent(lookback=20)
        result = agent.generate_signal(sample_prices)
        meta = result["metadata"]
        assert meta["n_assets"] == len(sample_prices.columns)
        assert meta["n_periods"] > 0
        assert "factors_used" in meta

    def test_deterministic(self, sample_prices):
        np.random.seed(42)
        agent = AlphaAgent(lookback=20)
        r1 = agent.generate_signal(sample_prices)
        np.random.seed(42)
        r2 = agent.generate_signal(sample_prices)
        assert r1["signal"] == r2["signal"]


# ── Risk Agent (G2) ──────────────────────────────────────────────────

class TestRiskAgent:
    def test_produces_valid_risk_report(self):
        np.random.seed(42)
        returns = np.random.normal(0.001, 0.02, 200)
        agent = RiskAgent()
        result = agent.evaluate(returns)
        assert "risk_report" in result
        assert "gate" in result
        assert "var_95" in result["risk_report"]
        assert "sharpe" in result["risk_report"]

    def test_gate_with_violations(self):
        np.random.seed(42)
        returns = np.random.normal(-0.01, 0.05, 200)  # bad returns
        agent = RiskAgent(thresholds={"sharpe": {"min": 5.0}})
        result = agent.evaluate(returns)
        assert result["gate"]["passed"] is False

    def test_with_benchmark_and_weights(self):
        np.random.seed(42)
        returns = np.random.normal(0.001, 0.02, 200)
        weights = np.array([0.4, 0.3, 0.3])
        agent = RiskAgent()
        result = agent.evaluate(returns, benchmark_returns=returns, weights=weights)
        assert result["risk_report"]["beta"] is not None
        assert result["risk_report"]["concentration"] is not None


# ── Orchestrator (G3) ────────────────────────────────────────────────

class TestOrchestrator:
    def test_returns_final_decision(self, sample_prices):
        orch = Orchestrator(lookback=20, train_window=60, test_window=20, seed=42)
        result = orch.run_pipeline(sample_prices)
        assert result["action"] in ("PROCEED", "REJECT")
        assert "signal" in result
        assert "backtest" in result
        assert "risk_report" in result
        assert "gate" in result

    def test_backtest_has_bootstrap_ci(self, sample_prices):
        orch = Orchestrator(lookback=20, train_window=60, test_window=20, seed=42)
        result = orch.run_pipeline(sample_prices)
        ci = result["backtest"]["bootstrap_ci"]
        assert "point_estimate" in ci
        assert "ci_lower" in ci
        assert "ci_upper" in ci


# ── HTTP Server (G6) ─────────────────────────────────────────────────

class TestHTTPServer:
    def test_agent_card_endpoint(self, client):
        resp = client.get("/agent-card")
        assert resp.status_code == 200
        data = resp.json()
        assert data["name"] == "QuantProto Orchestrator"
        assert "capabilities" in data

    def test_health(self, client):
        resp = client.get("/health")
        assert resp.status_code == 200

    def test_task_requires_auth(self, client):
        resp = client.post("/tasks", json={"prices": {"A": [1.0, 2.0]}})
        assert resp.status_code == 422 or resp.status_code == 401

    def test_task_with_valid_token(self, client, valid_token, sample_prices):
        price_dict = {col: sample_prices[col].tolist() for col in sample_prices.columns}
        resp = client.post(
            "/tasks",
            json={
                "prices": price_dict,
                "train_window": 60,
                "test_window": 20,
                "seed": 42,
            },
            headers={"Authorization": f"Bearer {valid_token}"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["action"] in ("PROCEED", "REJECT")

    def test_task_with_invalid_token(self, client):
        resp = client.post(
            "/tasks",
            json={"prices": {"A": [1.0] * 100}},
            headers={"Authorization": "Bearer invalid.token.here"},
        )
        assert resp.status_code == 401
