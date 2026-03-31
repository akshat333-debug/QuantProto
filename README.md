# QuantProto

> Reproducible quantitative research engine with alpha generation, risk evaluation, walk-forward backtesting, regime detection, and an interactive analytics dashboard.

[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://python.org)
[![Tests](https://img.shields.io/badge/tests-246%20passing-brightgreen.svg)]()
[![License](https://img.shields.io/badge/license-MIT-green.svg)]()

---

## Overview

QuantProto is a full-stack quantitative research platform that combines:

- **Factor Alpha Engine** — Momentum, mean-reversion, and volatility signals with composite scoring
- **Walk-Forward Backtester** — Out-of-sample validation with bootstrap Sharpe confidence intervals
- **HMM Regime Detection** — 3-state (Bull/Neutral/Bear) market regime identification
- **Risk Engine** — VaR, CVaR, Sharpe, Sortino, Beta, Calmar, pain index + risk gate system
- **Portfolio Optimisation** — Mean-Variance, Risk Parity, Max Sharpe, Black-Litterman
- **Stress Testing** — 5 historical crisis scenarios + Monte Carlo simulation
- **Interactive Dashboard** — Next.js frontend with 6 analysis tabs and real-time visualisation
- **MCP Tool Interface** — 14 quantitative tools exposed via FastMCP
- **Agent Orchestration** — A2A agent trio (Alpha → Risk → Decision) with JWT auth

## Quick Start

### Prerequisites

- Python 3.11+
- Node.js 18+ (for dashboard)
- Docker (optional, for full stack)

### 1. Install the backend

```bash
pip install -e ".[dev]"
```

### 2. Run the demo CLI

```bash
python -m quantproto.demo.run_demo
```

### 3. Start the API server

```bash
uvicorn quantproto.dashboard.api:app --host 0.0.0.0 --port 9000 --reload
```

### 4. Start the dashboard

```bash
cd dashboard
npm install
npm run dev
```

Open [http://localhost:3000](http://localhost:3000) — configure tickers, click **Run Analysis**, and explore the 6 tabs.

### 5. Run with Docker Compose (full stack)

```bash
docker compose up -d
```

Starts the app, TimescaleDB, and Redis.

## Dashboard

The interactive dashboard provides 6 analysis tabs:

| Tab | What it shows |
|-----|---------------|
| **Overview** | Key metrics (Sharpe, Sortino, VaR, Max DD), equity curve, asset breakdown |
| **Performance** | Full equity curve + drawdown chart |
| **Risk** | Correlation matrix, rolling correlation, PCA variance, gate violations |
| **Regime** | Regime states timeline, confidence chart, regime distribution |
| **Portfolio** | Pie charts (MV, Risk Parity, Max Sharpe) + allocation comparison bar chart |
| **Stress Test** | Historical crisis scenarios + Monte Carlo simulation paths |

## Project Structure

```
quantproto/
├── agents/          # A2A agent trio + orchestrator + JWT auth
├── analytics/       # Drawdown, correlation, PCA analytics
├── compliance/      # Audit log (hash-chained) + pre-trade checks
├── dashboard/       # FastAPI REST API + WebSocket dashboard
├── demo/            # Deterministic demo CLI
├── factor_engine.py # Factor alpha engine (momentum, MR, vol)
├── mcp/             # FastMCP server (14 tools + rate limiting)
├── ml/              # ML alpha models + feature store
├── portfolio/       # Portfolio optimisation (MV, RP, MS, BL)
├── regime_model.py  # HMM regime detection
├── risk/            # Stress tester (historical + Monte Carlo)
├── risk_engine.py   # Risk metrics + risk gate
├── strategy/        # Strategy framework + registry
├── trading/         # Paper broker (simulated execution)
└── walk_forward.py  # Walk-forward backtester + bootstrap CI

dashboard/           # Next.js 16 frontend
tests/               # 246 tests across 18 files
```

## Testing

```bash
# Run all backend tests
pytest

# Type-check the frontend
cd dashboard && npx tsc --noEmit

# Production build
cd dashboard && npm run build
```

## Environment Variables

### Dashboard (`dashboard/.env.local`)

| Variable | Default | Description |
|----------|---------|-------------|
| `API_URL` | `http://localhost:9000` | Backend API URL for Next.js proxy |

### Backend

| Variable | Default | Description |
|----------|---------|-------------|
| `ALLOWED_ORIGINS` | `http://localhost:3000` | CORS allowed origins (comma-separated) |
| `API_KEY` | *(none)* | Optional API key for auth (disabled if unset) |
| `REDIS_URL` | `redis://localhost:6379/0` | Redis connection URL |
| `DATABASE_URL` | *(none)* | TimescaleDB connection URL |

## License

MIT
