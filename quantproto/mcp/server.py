"""QuantProto MCP Server — exposes quant engine as MCP tools.

Usage (for testing):
    from quantproto.mcp.server import mcp
    # Then call tools programmatically or run with: python -m quantproto.mcp.server
"""

from __future__ import annotations

import time
import logging
from typing import Any

import numpy as np
import pandas as pd
from fastmcp import FastMCP

from quantproto.factor_engine import FactorAlphaEngine
from quantproto.risk_engine import RiskEngine
from quantproto.walk_forward import WalkForwardBacktester
from quantproto.regime_model import RegimeHMM
from quantproto.mcp.sanitize import (
    validate_prices_input,
    validate_returns_input,
    validate_positive_int,
    validate_confidence,
    validate_weights,
)
from quantproto.mcp.rate_limit import RateLimiter
from quantproto.logging_config import get_logger

logger = get_logger("mcp.server")
rate_limiter = RateLimiter(max_tokens=60, refill_rate=1.0)

mcp = FastMCP("QuantProto")


# ── Helpers ───────────────────────────────────────────────────────────

def _prices_to_df(prices: dict[str, list[float]]) -> pd.DataFrame:
    """Convert {ticker: [values]} dict to DataFrame."""
    return pd.DataFrame(prices)


def _df_to_dict(df: pd.DataFrame) -> dict[str, list[float]]:
    """Convert DataFrame to {col: [values]} dict."""
    return {col: df[col].tolist() for col in df.columns}


def _log_tool_call(tool_name: str, start: float, status: str = "ok") -> None:
    duration_ms = round((time.time() - start) * 1000, 2)
    logger.info(
        "tool_call",
        extra={"tool": tool_name, "duration_ms": duration_ms, "status": status},
    )


# ── Health ────────────────────────────────────────────────────────────

@mcp.tool()
def health() -> dict[str, str]:
    """Health check for the MCP server."""
    return {"status": "ok"}


# ══════════════════════════════════════════════════════════════════════
# ALPHA TOOLS (F2)
# ══════════════════════════════════════════════════════════════════════

@mcp.tool()
def compute_momentum(
    prices: dict[str, list[float]],
    lookback: int = 20,
) -> dict[str, Any]:
    """Compute momentum factor for given price data."""
    rate_limiter.consume()
    start = time.time()
    validate_prices_input(prices)
    validate_positive_int(lookback, "lookback", max_val=252)
    df = _prices_to_df(prices)
    result = FactorAlphaEngine.momentum_factor(df, lookback=lookback)
    _log_tool_call("compute_momentum", start)
    return {"factor": _df_to_dict(result)}


@mcp.tool()
def compute_mean_reversion(
    prices: dict[str, list[float]],
    lookback: int = 20,
) -> dict[str, Any]:
    """Compute mean-reversion (z-score) factor."""
    rate_limiter.consume()
    start = time.time()
    validate_prices_input(prices)
    validate_positive_int(lookback, "lookback", max_val=252)
    df = _prices_to_df(prices)
    result = FactorAlphaEngine.mean_reversion_factor(df, lookback=lookback)
    _log_tool_call("compute_mean_reversion", start)
    return {"factor": _df_to_dict(result)}


@mcp.tool()
def compute_volatility(
    returns: dict[str, list[float]],
    window: int = 20,
) -> dict[str, Any]:
    """Compute rolling volatility factor."""
    rate_limiter.consume()
    start = time.time()
    validate_prices_input(returns)  # same validation shape
    validate_positive_int(window, "window", max_val=252)
    df = _prices_to_df(returns)
    result = FactorAlphaEngine.volatility_factor(df, window=window)
    _log_tool_call("compute_volatility", start)
    return {"factor": _df_to_dict(result)}


@mcp.tool()
def compute_composite_signal(
    factors: dict[str, dict[str, list[float]]],
    weights: dict[str, float] | None = None,
) -> dict[str, Any]:
    """Compute composite alpha signal from multiple factors."""
    rate_limiter.consume()
    start = time.time()
    factor_dfs = {name: pd.DataFrame(data) for name, data in factors.items()}
    if weights is not None:
        validate_weights(weights)
    result = FactorAlphaEngine.composite_signal(factor_dfs, weights=weights)
    _log_tool_call("compute_composite_signal", start)
    return {"signal": _df_to_dict(result)}


# ══════════════════════════════════════════════════════════════════════
# RISK TOOLS (F3)
# ══════════════════════════════════════════════════════════════════════

@mcp.tool()
def compute_var(
    returns: list[float],
    confidence: float = 0.95,
) -> dict[str, float]:
    """Compute Historical Value-at-Risk."""
    rate_limiter.consume()
    start = time.time()
    validate_returns_input(returns)
    validate_confidence(confidence)
    var = RiskEngine.value_at_risk(np.array(returns), confidence=confidence)
    _log_tool_call("compute_var", start)
    return {"var": var}


@mcp.tool()
def compute_cvar(
    returns: list[float],
    confidence: float = 0.95,
) -> dict[str, float]:
    """Compute Conditional VaR (Expected Shortfall)."""
    rate_limiter.consume()
    start = time.time()
    validate_returns_input(returns)
    validate_confidence(confidence)
    cvar = RiskEngine.cvar(np.array(returns), confidence=confidence)
    _log_tool_call("compute_cvar", start)
    return {"cvar": cvar}


@mcp.tool()
def compute_sharpe(
    returns: list[float],
    rf: float = 0.0,
) -> dict[str, float]:
    """Compute annualised Sharpe ratio."""
    rate_limiter.consume()
    start = time.time()
    validate_returns_input(returns)
    sharpe = RiskEngine.sharpe_ratio(np.array(returns), rf=rf)
    _log_tool_call("compute_sharpe", start)
    return {"sharpe": sharpe}


@mcp.tool()
def compute_sortino(
    returns: list[float],
    rf: float = 0.0,
) -> dict[str, float]:
    """Compute annualised Sortino ratio."""
    rate_limiter.consume()
    start = time.time()
    validate_returns_input(returns)
    sortino = RiskEngine.sortino_ratio(np.array(returns), rf=rf)
    _log_tool_call("compute_sortino", start)
    return {"sortino": sortino}


@mcp.tool()
def compute_beta(
    returns: list[float],
    benchmark: list[float],
) -> dict[str, float]:
    """Compute regression beta against benchmark."""
    rate_limiter.consume()
    start = time.time()
    validate_returns_input(returns)
    validate_returns_input(benchmark)
    beta = RiskEngine.beta(np.array(returns), np.array(benchmark))
    _log_tool_call("compute_beta", start)
    return {"beta": beta}


@mcp.tool()
def compute_concentration(
    weights: list[float],
) -> dict[str, float]:
    """Compute HHI concentration risk."""
    rate_limiter.consume()
    start = time.time()
    hhi = RiskEngine.concentration_risk(np.array(weights))
    _log_tool_call("compute_concentration", start)
    return {"hhi": hhi}


@mcp.tool()
def risk_gate(
    metrics: dict[str, float],
    thresholds: dict[str, dict],
) -> dict[str, Any]:
    """Check risk metrics against thresholds."""
    rate_limiter.consume()
    start = time.time()
    result = RiskEngine.risk_gate(metrics, thresholds)
    _log_tool_call("risk_gate", start)
    return result


# ══════════════════════════════════════════════════════════════════════
# BACKTEST + REGIME TOOLS (F4)
# ══════════════════════════════════════════════════════════════════════

@mcp.tool()
def run_backtest(
    prices: dict[str, list[float]],
    train_window: int = 60,
    test_window: int = 20,
) -> dict[str, Any]:
    """Run walk-forward backtest with equal-weight signal."""
    rate_limiter.consume()
    start = time.time()
    validate_prices_input(prices)
    validate_positive_int(train_window, "train_window", max_val=504)
    validate_positive_int(test_window, "test_window", max_val=252)

    df = _prices_to_df(prices)

    def equal_weight_signal(train_prices: pd.DataFrame) -> pd.DataFrame:
        n_assets = train_prices.shape[1]
        return pd.DataFrame(
            np.ones_like(train_prices.values) / n_assets,
            index=train_prices.index,
            columns=train_prices.columns,
        )

    result = WalkForwardBacktester.run(df, equal_weight_signal, train_window, test_window)
    _log_tool_call("run_backtest", start)
    return {
        "returns": result["returns"].tolist(),
        "equity_curve": result["equity_curve"].tolist(),
        "n_splits": result["n_splits"],
    }


@mcp.tool()
def bootstrap_sharpe_ci(
    returns: list[float],
    n_boot: int = 1000,
    ci: float = 0.95,
    seed: int = 42,
) -> dict[str, float]:
    """Compute bootstrap confidence interval for Sharpe ratio."""
    rate_limiter.consume()
    start = time.time()
    validate_returns_input(returns)
    validate_positive_int(n_boot, "n_boot", max_val=10000)
    validate_confidence(ci)
    result = WalkForwardBacktester.bootstrap_sharpe_ci(
        np.array(returns), n_boot=n_boot, ci=ci, seed=seed,
    )
    _log_tool_call("bootstrap_sharpe_ci", start)
    return result


@mcp.tool()
def detect_regime(
    returns: list[float],
    window: int = 20,
    n_states: int = 3,
    seed: int = 42,
) -> dict[str, Any]:
    """Detect market regimes using HMM."""
    rate_limiter.consume()
    start = time.time()
    validate_returns_input(returns)
    validate_positive_int(window, "window", max_val=252)

    series = pd.Series(returns)
    model = RegimeHMM(n_states=n_states, seed=seed)
    features = model.engineer_features(series, window=window)
    model.fit(features)
    states = model.predict_states(features)
    confidence = model.posterior_confidence(features)
    _log_tool_call("detect_regime", start)
    return {
        "states": states.tolist(),
        "confidence": confidence.tolist(),
    }


# ── Entry point ───────────────────────────────────────────────────────

if __name__ == "__main__":
    mcp.run()
