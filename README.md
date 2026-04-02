# QuantProto

> Protocol-native quantitative research engine that exposes reproducible trading workflows — alpha generation, risk evaluation, walk-forward backtesting, regime detection — as MCP tools and orchestrates them via A2A agents with strict risk gating.

[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://python.org)
[![Tests](https://img.shields.io/badge/tests-246%20passing-brightgreen.svg)]()
[![CI](https://img.shields.io/github/actions/workflow/status/akshat333-debug/QuantProto/ci.yml?label=CI)](https://github.com/akshat333-debug/QuantProto/actions)

---

**Not a trading bot. Not a prediction model.**
This is infrastructure for building reproducible quant research systems — exposing correct methodology through agent protocols.

## What Makes It Different

| Principle | Implementation |
|-----------|---------------|
| **No overfitting** | Walk-forward backtester with bootstrap Sharpe confidence intervals — never tests on training data |
| **Non-stationarity handling** | HMM-based regime detection (Bull/Neutral/Bear) adjusts exposure before execution |
| **Risk-gated execution** | Threshold-based risk gate (VaR, Sharpe, concentration) — pipeline rejects before it trades |
| **Agent discoverability** | Core workflows exposed as MCP tools — any agent can discover and invoke them |
| **Deterministic reproducibility** | Seeded RNG on every stochastic path — same inputs always produce same outputs |

## Architecture

```
┌─────────────────── A2A Agent Layer ───────────────────┐
│                                                        │
│   AlphaAgent ──→ RegimeHMM ──→ Backtester ──→ RiskAgent  │
│       │              │              │              │   │
│   composite      3-state HMM    walk-forward    risk   │
│   signal         exposure adj   out-of-sample   gate   │
│                                                        │
│                  Orchestrator                          │
│              (chains pipeline, enforces gate)           │
└────────────────────────────────────────────────────────┘
         ↕ MCP Tools                    ↕ REST API
┌────────────────────┐       ┌────────────────────────┐
│  FastMCP Server    │       │  FastAPI Dashboard API  │
│  (agent-callable)  │       │  (human-facing)         │
└────────────────────┘       └────────────────────────┘
```

### Core Pipeline (what the orchestrator does)

1. **Alpha Signal** — Composite of momentum, mean-reversion, and volatility factors (cross-sectional percentile ranking + confidence weighting)
2. **Regime Detection** — 3-state Hidden Markov Model on engineered features (rolling returns, vol, vol-of-vol) — adjusts exposure per regime
3. **Walk-Forward Backtest** — Rolling train/test splits, never looks ahead. Bootstrap Sharpe CI quantifies statistical confidence
4. **Risk Gate** — Evaluates Sharpe, VaR, CVaR, Beta, concentration (HHI) against configurable thresholds. Pipeline halts if gate fails
5. **Decision** — `PROCEED` or `REJECT` — no blind automation

### MCP Tool Interface

The quant engine is exposed as MCP tools, making workflows agent-discoverable:

| Tool | What it does |
|------|-------------|
| `run_backtest` | Walk-forward backtest with configurable windows |
| `detect_regime` | HMM regime detection with confidence scores |
| `risk_gate` | Threshold check — go/no-go decision |
| `compute_composite_signal` | Weighted factor combination with rank-based scoring |

Additional tools expose individual risk metrics (VaR, CVaR, Sharpe, Sortino, Beta, HHI) and factor computations for granular agent workflows. All tools include rate limiting and input sanitization.

### A2A Agent Orchestration

Three agents coordinate via the Orchestrator pattern:

- **AlphaAgent** — Generates composite factor signals from price data
- **RiskAgent** — Evaluates returns against risk thresholds, produces go/no-go gate
- **Orchestrator** — Chains the full pipeline: `Alpha → Regime → Backtest → Risk → Decision`

Agents authenticate via JWT. The orchestrator enforces the risk gate — if risk thresholds are violated, the pipeline rejects regardless of alpha signal quality.

## Quick Start

```bash
# Install
pip install -e ".[dev]"

# Run the demo pipeline (deterministic, seeded)
python -m quantproto.demo.run_demo

# Run the full test suite (246 tests)
pytest
```

### API + Dashboard (optional)

```bash
# Start the API server
uvicorn quantproto.dashboard.api:app --host 0.0.0.0 --port 9000 --reload

# Start the dashboard (separate terminal)
cd dashboard && npm install && npm run dev
```

### Docker (full stack)

```bash
docker compose up -d
# Starts: API (:9000), Dashboard (:3000), TimescaleDB, Redis
```

## Project Structure

```
quantproto/
├── agents/            # A2A: AlphaAgent, RiskAgent, Orchestrator, JWT auth
├── mcp/               # FastMCP server — tool interface with rate limiting
├── factor_engine.py   # Factor alpha (momentum, mean-reversion, volatility, composite)
├── risk_engine.py     # Risk metrics (Sharpe, Sortino, VaR, CVaR, Beta, HHI) + risk gate
├── regime_model.py    # HMM regime detection (3-state, feature engineering)
├── walk_forward.py    # Walk-forward backtester + bootstrap Sharpe CI
├── execution_model.py # Slippage + transaction cost simulation
├── analytics/         # Drawdown, correlation, PCA
├── portfolio/         # Optimisation (Mean-Variance, Risk Parity, Max Sharpe, Black-Litterman)
├── risk/              # Stress testing (5 crisis scenarios + Monte Carlo)
├── compliance/        # Audit log (hash-chained) + pre-trade checks
├── data/              # DataFetcher (yfinance + CSV cache), UniverseManager
├── strategy/          # Strategy framework + registry
├── trading/           # Paper broker (simulated execution)
└── dashboard/         # FastAPI REST API

dashboard/             # Next.js frontend (optional visualization layer)
tests/                 # 246 tests across 18 files
.github/workflows/     # CI: pytest (Python 3.11+3.12) + tsc + next build
```

## Testing

246 tests covering:
- Factor computation correctness
- Walk-forward split integrity
- Bootstrap CI statistical properties
- Regime model state transitions
- Risk gate threshold logic
- Agent orchestration pipeline
- Execution model slippage accuracy
- Stress test scenario bounds

```bash
pytest                              # Full suite
pytest tests/test_walk_forward.py   # Just backtester
pytest tests/test_risk.py           # Just risk engine
```

## Environment Variables

| Variable | Description |
|----------|-------------|
| `GEMINI_API_KEY` | Optional — enables AI-powered analysis summaries |
| `ALLOWED_ORIGINS` | CORS origins for API (default: `http://localhost:3000`) |
| `API_KEY` | Optional API key auth (disabled if unset) |

## License

MIT
