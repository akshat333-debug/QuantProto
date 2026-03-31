"""Dashboard REST API — serves real analysis data to the Next.js frontend.

Runs alongside the A2A server. Provides endpoints for:
- /api/run-analysis — run full pipeline, return all data for visualization
- /api/strategies — list available strategies
- /api/stress-test — run stress scenario

Security:
- CORS restricted to ALLOWED_ORIGINS env var (default: http://localhost:3000)
- Optional API key via API_KEY env var (skipped if not set = dev mode)
"""

from __future__ import annotations

import os
import re
from typing import Literal

import numpy as np
import pandas as pd
from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field, field_validator

from quantproto.demo.data_loader import generate_prices
from quantproto.data.fetcher import fetch_prices
from quantproto.factor_engine import FactorAlphaEngine
from quantproto.risk_engine import RiskEngine
from quantproto.walk_forward import WalkForwardBacktester
from quantproto.regime_model import RegimeHMM
from quantproto.analytics import DrawdownAnalytics
from quantproto.analytics.correlation import CorrelationEngine
from quantproto.portfolio.optimiser import PortfolioOptimiser
from quantproto.risk.stress import StressTester
from quantproto.genai import generate_summary, chat as genai_chat, is_available as genai_available

app = FastAPI(title="QuantProto Dashboard API", version="0.1.0")

# ── CORS — restricted origins ──────────────────────────────────────────
_raw_origins = os.getenv("ALLOWED_ORIGINS", "http://localhost:3000")
ALLOWED_ORIGINS = [o.strip() for o in _raw_origins.split(",") if o.strip()]

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["Content-Type", "X-API-Key"],
)

# ── Optional API key auth ──────────────────────────────────────────────
API_KEY = os.getenv("API_KEY")  # None = dev mode (no auth)


@app.middleware("http")
async def api_key_auth(request: Request, call_next):
    """Validate X-API-Key header if API_KEY env var is set."""
    if API_KEY is not None:
        # Skip auth for health, docs, and CORS preflight
        if request.method == "OPTIONS" or request.url.path in ("/api/health", "/docs", "/openapi.json"):
            return await call_next(request)
        key = request.headers.get("X-API-Key")
        if key != API_KEY:
            return JSONResponse(status_code=401, content={"detail": "Invalid or missing API key"})
    return await call_next(request)


# ── Request models with validation ────────────────────────────────────
_TICKER_RE = re.compile(r"^[A-Z0-9]{1,10}$")


class AnalysisRequest(BaseModel):
    tickers: list[str] = Field(default=["AAPL", "GOOG", "MSFT", "AMZN", "META"], min_length=1, max_length=20)
    n_days: int = Field(default=504, ge=10, le=5000)
    seed: int = Field(default=42, ge=0, le=999999)
    train_window: int = Field(default=60, ge=5, le=500)
    test_window: int = Field(default=20, ge=5, le=200)
    lookback: int = Field(default=20, ge=5, le=200)
    data_source: Literal["synthetic", "live"] = Field(default="synthetic")
    start_date: str = Field(default="2020-01-01")
    end_date: str = Field(default="2024-01-01")

    @field_validator("tickers", mode="before")
    @classmethod
    def normalise_tickers(cls, v: list[str]) -> list[str]:
        out = [t.strip().upper() for t in v if t.strip()]
        if not out:
            raise ValueError("At least one ticker is required")
        for t in out:
            if not _TICKER_RE.match(t):
                raise ValueError(f"Invalid ticker: {t!r} (1-10 uppercase alphanumeric chars)")
        return out

    @field_validator("start_date", "end_date")
    @classmethod
    def valid_date(cls, v: str) -> str:
        if not re.match(r"^\d{4}-\d{2}-\d{2}$", v):
            raise ValueError(f"Invalid date format: {v!r} (expected YYYY-MM-DD)")
        return v


class StressRequest(BaseModel):
    scenario: str = Field(default="2008_crisis")
    seed: int = Field(default=42, ge=0, le=999999)

    @field_validator("scenario")
    @classmethod
    def valid_scenario(cls, v: str) -> str:
        valid = set(StressTester.SCENARIOS.keys())
        if v not in valid:
            raise ValueError(f"Unknown scenario: {v!r}. Valid: {sorted(valid)}")
        return v


@app.get("/api/health")
def health():
    return {"status": "ok"}


@app.post("/api/run-analysis")
def run_analysis(req: AnalysisRequest):
    """Run the full QuantProto pipeline and return all data for the dashboard."""

    # 1. Get prices (live from Yahoo Finance or synthetic)
    if req.data_source == "live":
        prices = fetch_prices(req.tickers, start=req.start_date, end=req.end_date)
        if prices.empty:
            raise HTTPException(status_code=400, detail="No data returned for the given tickers/date range. Check ticker symbols and dates.")
    else:
        prices = generate_prices(req.tickers, n_days=req.n_days, seed=req.seed)
    returns = prices.pct_change().dropna()

    # 2. Factor signals
    engine = FactorAlphaEngine()
    momentum = engine.momentum_factor(prices, lookback=req.lookback)
    mean_rev = engine.mean_reversion_factor(prices, lookback=req.lookback)
    volatility = engine.volatility_factor(returns, window=req.lookback)

    factors = {
        "momentum": momentum,
        "mean_reversion": mean_rev,
        "volatility": volatility,
    }
    composite = engine.composite_signal(factors)

    # 3. Portfolio optimisation
    mu = returns.mean().values * 252
    cov = returns.cov().values * 252
    mv_weights = PortfolioOptimiser.mean_variance(mu, cov)
    rp_weights = PortfolioOptimiser.risk_parity(cov)
    ms_weights = PortfolioOptimiser.max_sharpe(mu, cov)

    # 4. Backtest
    def signal_fn(train):
        n = train.shape[1]
        return pd.DataFrame(
            np.ones((len(train), n)) / n,
            index=train.index,
            columns=train.columns,
        )

    bt_result = WalkForwardBacktester.run(
        prices, signal_fn, req.train_window, req.test_window
    )
    equity_values = bt_result["equity_curve"].values.tolist()
    equity_dates = [str(d.date()) for d in bt_result["equity_curve"].index]
    bt_returns = bt_result["returns"].values

    # 5. Bootstrap Sharpe CI
    ci = WalkForwardBacktester.bootstrap_sharpe_ci(bt_returns, seed=req.seed)

    # 6. Risk metrics
    sharpe = float(RiskEngine.sharpe_ratio(bt_returns))
    sortino = float(RiskEngine.sortino_ratio(bt_returns))
    var_95 = float(RiskEngine.value_at_risk(bt_returns, 0.95))
    cvar_95 = float(RiskEngine.cvar(bt_returns, 0.95))

    # 7. Drawdown analytics
    eq_arr = np.array(equity_values)
    dd_series = DrawdownAnalytics.drawdown_series(eq_arr)
    max_dd = DrawdownAnalytics.max_drawdown(eq_arr)
    calmar = DrawdownAnalytics.calmar_ratio(bt_returns, eq_arr)
    pain = DrawdownAnalytics.pain_index(eq_arr)
    uw_periods = DrawdownAnalytics.underwater_periods(eq_arr)

    # 8. Regime detection
    hmm = RegimeHMM(seed=req.seed)
    mean_ret = returns.mean(axis=1)
    features = hmm.engineer_features(mean_ret, window=req.lookback)
    hmm.fit(features)
    regime_states = hmm.predict_states(features)
    regime_confidence = hmm.posterior_confidence(features)

    # Align regime data with equity dates
    regime_dates = [str(d.date()) for d in regime_states.index]
    regime_values = regime_states.values.tolist()
    confidence_values = regime_confidence.values.tolist()

    # 9. Correlation
    corr_matrix = returns.corr()
    rolling_corr = CorrelationEngine.rolling_correlation(returns, window=30)
    pca = CorrelationEngine.pca_decomposition(returns, n_components=min(3, len(req.tickers)))

    # 10. Per-asset stats
    asset_stats = []
    for ticker in req.tickers:
        r = returns[ticker].values
        asset_stats.append({
            "ticker": ticker,
            "annualised_return": float(np.mean(r) * 252 * 100),
            "annualised_vol": float(np.std(r) * np.sqrt(252) * 100),
            "sharpe": float(RiskEngine.sharpe_ratio(r)),
            "max_drawdown": float(DrawdownAnalytics.max_drawdown(
                np.cumprod(1 + r)
            ) * 100),
            "latest_price": float(prices[ticker].iloc[-1]),
        })

    # 11. Risk gate
    gate = RiskEngine.risk_gate(
        {"var": var_95, "sharpe": sharpe},
        {"var": {"max": -0.05}, "sharpe": {"min": 0.5}},
    )

    return {
        "summary": {
            "action": "PROCEED" if gate["passed"] else "REJECT",
            "sharpe": round(sharpe, 4),
            "sortino": round(sortino, 4),
            "var_95": round(var_95 * 100, 2),
            "cvar_95": round(cvar_95 * 100, 2),
            "max_drawdown": round(max_dd * 100, 2),
            "calmar": round(calmar, 4),
            "pain_index": round(pain * 100, 2),
            "total_return": round((eq_arr[-1] / eq_arr[0] - 1) * 100, 2),
            "n_splits": bt_result["n_splits"],
            "bootstrap_ci": {
                "lower": round(ci["ci_lower"], 2),
                "upper": round(ci["ci_upper"], 2),
                "point": round(ci["point_estimate"], 2),
            },
            "gate_passed": gate["passed"],
            "gate_violations": gate["violations"],
        },
        "equity_curve": {
            "dates": equity_dates,
            "values": [round(v, 4) for v in equity_values],
        },
        "drawdown": {
            "dates": equity_dates,
            "values": [round(float(v) * 100, 2) for v in dd_series],
        },
        "regime": {
            "dates": regime_dates,
            "states": regime_values,
            "confidence": [round(float(v), 3) for v in confidence_values],
        },
        "portfolio": {
            "tickers": req.tickers,
            "mean_variance": [round(float(w) * 100, 1) for w in mv_weights],
            "risk_parity": [round(float(w) * 100, 1) for w in rp_weights],
            "max_sharpe": [round(float(w) * 100, 1) for w in ms_weights],
        },
        "correlation": {
            "tickers": req.tickers,
            "matrix": [[round(float(corr_matrix.iloc[i, j]), 3) for j in range(len(req.tickers))] for i in range(len(req.tickers))],
        },
        "pca": {
            "explained_variance": [round(float(v) * 100, 1) for v in pca["explained_variance_ratio"]],
            "components": [f"PC{i+1}" for i in range(len(pca["explained_variance_ratio"]))],
        },
        "assets": asset_stats,
        "rolling_correlation": {
            "dates": [str(d.date()) for d in rolling_corr.index[-100:]],
            "values": [round(float(v), 3) for v in rolling_corr.values[-100:]],
        },
    }


@app.post("/api/stress-test")
def stress_test(req: StressRequest):
    """Run a stress test scenario."""
    np.random.seed(42)
    base_returns = np.random.normal(0.001, 0.02, 252)

    result = StressTester.historical_scenario(base_returns, req.scenario, req.seed)
    mc = StressTester.monte_carlo(base_returns, n_simulations=500, horizon=126, seed=req.seed)

    return {
        "scenario": {
            "name": req.scenario,
            "max_drawdown": round(result["max_drawdown"] * 100, 2),
            "total_return": round(result["total_return"] * 100, 2),
            "worst_day": round(result["worst_day"] * 100, 2),
            "var_95": round(result["var_95"] * 100, 2),
            "equity": [round(float(v), 4) for v in result["equity_curve"]],
        },
        "monte_carlo": {
            "median_terminal": round(mc["median_terminal"], 4),
            "p5": round(mc["percentile_5"], 4),
            "p95": round(mc["percentile_95"], 4),
            "prob_loss": round(mc["prob_loss"] * 100, 1),
            "worst_dd": round(mc["worst_max_dd"] * 100, 2),
            "paths": mc["sample_paths"],
        },
    }


@app.get("/api/scenarios")
def list_scenarios():
    return {"scenarios": list(StressTester.SCENARIOS.keys())}


# ── GenAI endpoints ───────────────────────────────────────────────────

class SummaryRequest(BaseModel):
    analysis_data: dict

class ChatRequest(BaseModel):
    question: str = Field(min_length=1, max_length=2000)
    analysis_data: dict | None = None


@app.get("/api/ai/status")
def ai_status():
    """Check if GenAI (Gemini) is available."""
    return {"available": genai_available()}


@app.post("/api/ai/summary")
def ai_summary(req: SummaryRequest):
    """Generate an AI executive summary of analysis results."""
    text = generate_summary(req.analysis_data)
    return {"summary": text, "ai_powered": genai_available()}


@app.post("/api/ai/chat")
def ai_chat(req: ChatRequest):
    """Chat with AI about analysis results."""
    response = genai_chat(req.question, req.analysis_data)
    return {"response": response, "ai_powered": genai_available()}
