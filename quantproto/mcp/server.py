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
from quantproto.integrity.deflated_sharpe import (
    probabilistic_sharpe_ratio,
    deflated_sharpe_ratio,
    _sample_stats,
)
from quantproto.integrity.pbo import pbo_cscv
from quantproto.integrity.cost_sensitivity import cost_sensitivity_sweep
from quantproto.integrity.score import robustness_report
from quantproto.mcp.sanitize import (
    validate_prices_input,
    validate_returns_input,
    validate_positive_int,
    validate_confidence,
    validate_weights,
)
from quantproto.mcp.rate_limit import build_rate_limiter
from quantproto.logging_config import get_logger

logger = get_logger("mcp.server")
# Redis-backed when REDIS_URL is set and reachable; in-memory otherwise.
rate_limiter = build_rate_limiter(max_tokens=60, refill_rate=1.0)

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


# ══════════════════════════════════════════════════════════════════════
# INTEGRITY / OVERFITTING-AUDIT TOOLS (the flagship — agent-callable)
# ══════════════════════════════════════════════════════════════════════

@mcp.tool()
def probabilistic_sharpe(
    returns: list[float],
    sharpe_benchmark: float = 0.0,
) -> dict[str, Any]:
    """Probability the *true* (per-period) Sharpe exceeds a benchmark.

    Corrects for sample length and non-normality (skew/kurtosis).
    """
    rate_limiter.consume()
    start = time.time()
    validate_returns_input(returns)
    sr, g3, g4, n = _sample_stats(np.array(returns))
    psr = probabilistic_sharpe_ratio(sr, n, g3, g4, sharpe_benchmark)
    _log_tool_call("probabilistic_sharpe", start)
    return {"psr": psr, "sharpe_per_period": sr, "skew": g3, "kurtosis": g4, "n": n}


@mcp.tool()
def deflated_sharpe(
    returns: list[float],
    n_trials: int = 1,
    var_sharpe: float = 0.0,
) -> dict[str, Any]:
    """Deflated Sharpe Ratio — PSR corrected for multiple-testing selection bias.

    ``n_trials`` = how many strategy configurations were tried; ``var_sharpe`` =
    variance of their Sharpe ratios. A low value means the Sharpe is plausibly
    the best of many lucky tries.
    """
    rate_limiter.consume()
    start = time.time()
    validate_returns_input(returns)
    validate_positive_int(n_trials, "n_trials", max_val=1_000_000)
    sr, g3, g4, n = _sample_stats(np.array(returns))
    res = deflated_sharpe_ratio(sr, n, n_trials, var_sharpe, g3, g4)
    _log_tool_call("deflated_sharpe", start)
    return res


@mcp.tool()
def prob_backtest_overfit(
    perf_matrix: list[list[float]],
    n_splits: int = 16,
) -> dict[str, Any]:
    """Probability of Backtest Overfitting via CSCV.

    ``perf_matrix`` is rows = time, columns = strategy configurations (≥ 2).
    Returns the PBO, OOS performance degradation, and P(OOS loss).
    """
    rate_limiter.consume()
    start = time.time()
    matrix = np.asarray(perf_matrix, dtype=float)
    result = pbo_cscv(matrix, n_splits=n_splits)
    _log_tool_call("prob_backtest_overfit", start)
    # Drop the (potentially large) raw logit list from the tool response.
    return {k: v for k, v in result.items() if k != "logits"}


@mcp.tool()
def cost_sensitivity(
    returns: list[float],
    turnover: float = 1.0,
) -> dict[str, Any]:
    """Transaction-cost sensitivity: net Sharpe across a cost grid + break-even bps."""
    rate_limiter.consume()
    start = time.time()
    validate_returns_input(returns)
    result = cost_sensitivity_sweep(np.array(returns), turnover=turnover)
    _log_tool_call("cost_sensitivity", start)
    return result


@mcp.tool()
def robustness_audit(
    returns: list[float],
    n_trials: int = 1,
    turnover: float = 1.0,
    variant_matrix: list[list[float]] | None = None,
) -> dict[str, Any]:
    """All-in-one overfitting audit → Robustness Score (0–100) + verdict.

    Works on any backtest. Supply ``returns`` (required) and optionally a
    ``variant_matrix`` (time × configurations) to also compute PBO. Returns the
    full report: score, verdict, component breakdown, statistics, red flags, and
    the manual integrity checklist.
    """
    rate_limiter.consume()
    start = time.time()
    validate_returns_input(returns)
    validate_positive_int(n_trials, "n_trials", max_val=1_000_000)
    vm = np.asarray(variant_matrix, dtype=float) if variant_matrix is not None else None
    report = robustness_report(
        np.array(returns), n_trials=n_trials, turnover=turnover, variant_matrix=vm,
    )
    _log_tool_call("robustness_audit", start)
    return report


# ══════════════════════════════════════════════════════════════════════
# EXPERIMENT TRACKER TOOLS (audit gate for agentic strategy search)
# ══════════════════════════════════════════════════════════════════════
#
# Agents that generate and iterate on strategies should call ``log_run``
# after every backtest and ``research_budget`` before promoting a result.
# The trial count that deflates the Sharpe is then observed, not claimed.

@mcp.tool()
def log_run(
    experiment: str,
    returns: list[float],
    params: dict[str, Any] | None = None,
    source: str = "mcp",
) -> dict[str, Any]:
    """Log one backtest run into the tamper-evident experiment ledger.

    Call after EVERY configuration you try — including failures and dead
    ends. The honest trial count is what makes the overfitting statistics
    meaningful. Returns the ledger receipt plus the updated budget state.
    """
    rate_limiter.consume()
    start = time.time()
    validate_returns_input(returns)
    from quantproto.tracker import experiment as open_experiment

    exp = open_experiment(experiment)
    receipt = exp.log(returns, params=params, source=source)
    status = exp.status()
    _log_tool_call("log_run", start)
    return {
        "receipt": receipt,
        "budget_state": status["budget_state"],
        "n_configs": status["n_configs"],
        "message": status["message"],
    }


@mcp.tool()
def research_budget(experiment: str) -> dict[str, Any]:
    """Research-budget meter for a tracked experiment.

    Computes, from the logged search history: the honest trial count, best
    vs expected-max-spurious annualized Sharpe, DSR, PBO (when ≥ 8 configs),
    haircut Sharpe, and a burned/warning/ok verdict. Use as a go/no-go gate
    before trusting or promoting any strategy from this experiment.
    """
    rate_limiter.consume()
    start = time.time()
    from quantproto.tracker import experiment as open_experiment

    status = open_experiment(experiment).status()
    _log_tool_call("research_budget", start)
    return status


@mcp.tool()
def log_live(
    experiment: str,
    returns: list[float],
    params: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Log live fills for drift tracking (excluded from the trial/config count).

    Call as live P&L accrues for a deployed strategy. Use ``live_drift`` to
    test whether the live track record is still consistent with the backtest
    that justified deploying it.
    """
    rate_limiter.consume()
    start = time.time()
    validate_returns_input(returns)
    from quantproto.tracker import experiment as open_experiment

    exp = open_experiment(experiment)
    receipt = exp.log_live(returns, params=params)
    _log_tool_call("log_live", start)
    return {"receipt": receipt, "drift": exp.drift()}


@mcp.tool()
def live_drift(experiment: str) -> dict[str, Any]:
    """Test whether live performance is still consistent with the backtest.

    Compares logged live fills against the best backtest config using a
    Probabilistic-Sharpe two-sample test. States: consistent / watch /
    diverging / no_live_data / no_backtest. Use as a decay alarm for
    deployed strategies.
    """
    rate_limiter.consume()
    start = time.time()
    from quantproto.tracker import experiment as open_experiment

    result = open_experiment(experiment).drift()
    _log_tool_call("live_drift", start)
    return result


@mcp.tool()
def experiment_report(experiment: str, turnover: float = 1.0) -> dict[str, Any]:
    """Full robustness report of an experiment's best config.

    The variant matrix and trial count are taken from the ledger, so PBO and
    the Deflated Sharpe reflect the real search. Includes chain-validity so
    the report can serve as a provenance certificate.
    """
    rate_limiter.consume()
    start = time.time()
    from quantproto.tracker import experiment as open_experiment

    report = open_experiment(experiment).report(turnover=turnover)
    _log_tool_call("experiment_report", start)
    return report


# ── Entry point ───────────────────────────────────────────────────────

if __name__ == "__main__":
    mcp.run()
