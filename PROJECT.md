# QuantProto — Reproducible Quant Research Engine

## Goal

A production-grade quantitative research platform combining alpha generation, risk evaluation, walk-forward backtesting, regime detection, portfolio optimisation, and agent-based orchestration — accessible via an interactive Next.js dashboard, an MCP tool interface, and a deterministic CLI.

## Tech Stack

| Layer        | Technology                                                               |
|--------------|--------------------------------------------------------------------------|
| **Frontend** | Next.js 16 (App Router), Recharts, Tailwind CSS 4, Lucide, next-themes  |
| **API**      | FastAPI (REST dashboard API, port 9000) + FastAPI WebSocket dashboard    |
| **Backend**  | Python 3.11, NumPy, pandas, SciPy, scikit-learn, hmmlearn               |
| **MCP**      | FastMCP — exposes quant engine as tool endpoints                         |
| **Agents**   | A2A agent trio (Alpha → Risk → Orchestrator) with JWT auth              |
| **Infra**    | Docker Compose (app + TimescaleDB + Redis)                               |

## Architecture

```
quantproto/
├── agents/         # A2A: AlphaAgent, RiskAgent, Orchestrator, HTTP server, JWT auth
├── analytics/      # DrawdownAnalytics, CorrelationEngine, PCA
├── backtest/       # Walk-forward engine (alternative import path)
├── compliance/     # AuditLog (hash-chained), PreTradeCompliance
├── compute/        # Parallel compute utilities
├── dashboard/      # FastAPI REST API (api.py) + WebSocket dashboard (__init__.py)
├── data/           # DataFetcher, UniverseManager
├── demo/           # Deterministic demo CLI + data loader
├── factors/        # Extended factor library
├── ml/             # ML alpha models, feature store
├── mcp/            # FastMCP server (14 tools), rate limiting, input sanitization
├── portfolio/      # PortfolioOptimiser (MV, risk parity, max-Sharpe, Black-Litterman)
├── regime/         # Regime module (alternative import path)
├── risk/           # StressTester (historical scenarios, Monte Carlo)
├── strategy/       # BaseStrategy, MultiStrategy, StrategyRegistry
├── trading/        # PaperBroker (simulated execution)
├── factor_engine.py    # Core factor alpha engine
├── risk_engine.py      # RiskEngine (Sharpe, Sortino, VaR, CVaR, Beta, risk gate)
├── regime_model.py     # RegimeHMM (3-state Hidden Markov Model)
├── walk_forward.py     # WalkForwardBacktester + bootstrap Sharpe CI
├── execution_model.py  # Slippage + transaction cost models
└── logging_config.py   # Structured JSON logging

dashboard/              # Next.js 16 frontend
├── src/app/page.tsx    # 780-line dashboard (6 tabs)
├── src/app/layout.tsx  # Root layout with next/font Inter
├── next.config.ts      # API proxy + security headers
└── .env.local          # API_URL config

tests/                  # 246 passing tests across 18 files
```

## Core Features

### Quant Engine
- Factor-based alpha engine (momentum, mean-reversion, volatility, composite signals)
- Walk-forward backtester with deterministic seeding
- Bootstrap Sharpe confidence intervals
- HMM-based regime detection (3-state: BULL/NEUTRAL/BEAR)
- Risk gate system (threshold-based go/no-go)

### Portfolio & Risk
- Portfolio optimisation: Mean-Variance, Risk Parity, Max Sharpe, Black-Litterman
- Risk metrics: Sharpe, Sortino, VaR, CVaR, Beta, concentration (HHI)
- Drawdown analytics: max drawdown, Calmar ratio, pain index, underwater periods
- Correlation engine + PCA decomposition
- Stress testing: 5 historical scenarios + Monte Carlo simulation

### Infrastructure
- MCP tool interface (14 tools with rate limiting + input sanitization)
- A2A agent trio with JWT auth + HTTP server
- Pre-trade compliance checks + hash-chained audit log
- Paper trading broker (simulated execution with PnL attribution)
- Docker Compose deployment (app + TimescaleDB + Redis)

### Dashboard (Next.js)
- 6 interactive tabs: Overview, Performance, Risk, Regime, Portfolio, Stress Test
- API proxied through Next.js rewrites (no hardcoded URLs)
- ARIA-compliant tab navigation, labeled inputs, accessible theme toggle
- Inline error banners for API failures
- Dynamic scenario list from backend
- Security headers (CSP, HSTS, X-Frame-Options)

## Constraints

- Deterministic runs (seeded RNG everywhere)
- No unsafe shell execution
- JWT-based A2A auth
- Strict MCP contract validation
- Structured JSON logging
- Rate limiting + input sanitization
- CORS restricted to allowed origins

## Status

- **Backend**: ✅ Complete (246/246 tests passing)
- **Frontend**: ✅ Functional (tsc + next build pass)
- **Uncommitted**: Audit fixes (CORS, auth, a11y, validation, docs) — ready to commit
