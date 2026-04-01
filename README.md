# QuantProto

> Reproducible quantitative research engine with alpha generation, risk evaluation, walk-forward backtesting, regime detection, GenAI analysis, and an interactive analytics dashboard.

[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://python.org)
[![Tests](https://img.shields.io/badge/tests-246%20passing-brightgreen.svg)]()
[![CI](https://img.shields.io/github/actions/workflow/status/akshat333-debug/QuantProto/ci.yml?label=CI)](https://github.com/akshat333-debug/QuantProto/actions)
[![License](https://img.shields.io/badge/license-MIT-green.svg)]()

---

## Overview

QuantProto is a full-stack quantitative research platform that combines:

- **Factor Alpha Engine** — Momentum, mean-reversion, and volatility signals with configurable composite scoring
- **Walk-Forward Backtester** — Out-of-sample validation with bootstrap Sharpe confidence intervals
- **HMM Regime Detection** — 3-state (Bull/Neutral/Bear) market regime identification
- **Risk Engine** — VaR, CVaR, Sharpe, Sortino, Beta, Calmar, pain index + risk gate system
- **Portfolio Optimisation** — Mean-Variance, Risk Parity, Max Sharpe, Black-Litterman
- **Stress Testing** — 5 historical crisis scenarios + Monte Carlo simulation
- **Live Market Data** — Yahoo Finance integration with local CSV caching (synthetic fallback)
- **GenAI Analysis** — Gemini-powered executive summaries and conversational chat
- **Interactive Dashboard** — Next.js frontend with 6 tabs, data export, and strategy builder
- **MCP Tool Interface** — 14 quantitative tools exposed via FastMCP
- **Agent Orchestration** — A2A agent trio (Alpha → Risk → Decision) with JWT auth

## Quick Start

### Prerequisites

- Python 3.11+
- Node.js 22+ (for dashboard)
- Docker (optional, for full stack)

### 1. Install the backend

```bash
pip install -e ".[dev,live,ai]"
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

Open [http://localhost:3000](http://localhost:3000) — configure tickers, adjust factor weights, click **Run Analysis**, and explore all 6 tabs.

### 5. Run with Docker Compose (full stack)

```bash
docker compose up -d
```

This starts 4 services: API (`:9000`), Dashboard (`:3000`), TimescaleDB (`:5432`), and Redis (`:6379`).

## Dashboard Features

| Tab | What it shows |
|-----|---------------|
| **Overview** | AI executive summary, key metrics (Sharpe, Sortino, VaR, Max DD), equity curve, asset breakdown |
| **Performance** | Full equity curve + drawdown chart |
| **Risk** | Correlation heatmap, rolling correlation, PCA variance, risk gate violations |
| **Regime** | Regime states timeline, confidence chart, regime distribution |
| **Portfolio** | Pie charts (MV, Risk Parity, Max Sharpe) + allocation comparison |
| **Stress Test** | Historical crisis scenarios + Monte Carlo simulation paths |

### Additional Features

- **Data Source Toggle** — Switch between synthetic data and live Yahoo Finance data with date range picker
- **Strategy Builder** — Interactive factor weight sliders (momentum, mean-reversion, volatility) with visual proportion bar
- **AI Chat** — Floating chat panel for asking questions about your analysis (powered by Gemini or mock fallback)
- **Export** — Download analysis results as CSV or JSON
- **Dark/Light Mode** — System-aware theme toggle
- **Mobile Responsive** — Optimized for all screen sizes

## Project Structure

```
quantproto/
├── agents/            # A2A agent trio + orchestrator + JWT auth
├── analytics/         # Drawdown, correlation, PCA analytics
├── compliance/        # Audit log (hash-chained) + pre-trade checks
├── dashboard/         # FastAPI REST API + WebSocket dashboard
├── data/              # DataFetcher (yfinance + cache), UniverseManager
├── demo/              # Deterministic demo CLI + data loader
├── genai/             # Gemini AI integration (summary, chat, mock fallback)
├── factor_engine.py   # Factor alpha engine (momentum, MR, vol, composite)
├── mcp/               # FastMCP server (14 tools + rate limiting)
├── ml/                # ML alpha models + feature store
├── portfolio/         # Portfolio optimisation (MV, RP, MS, BL)
├── regime_model.py    # HMM regime detection (3-state)
├── risk/              # Stress tester (historical + Monte Carlo)
├── risk_engine.py     # Risk metrics + risk gate
├── strategy/          # Strategy framework + registry
├── trading/           # Paper broker (simulated execution)
└── walk_forward.py    # Walk-forward backtester + bootstrap CI

dashboard/             # Next.js 16 frontend
├── src/app/           # Page orchestrator
├── src/components/    # Modular UI + tab components
│   ├── tabs/          # OverviewTab, PerformanceTab, RiskTab, etc.
│   └── ui/            # MetricCard, ChatPanel, AISummary, ExportPanel, etc.
├── src/lib/           # API client + shared types
├── Dockerfile         # Multi-stage production build
└── next.config.ts     # API proxy + security headers + standalone output

tests/                 # 246 tests across 18 files
.github/workflows/     # CI: pytest (Python 3.11+3.12) + tsc + next build
```

## API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/health` | GET | Health check |
| `/api/run-analysis` | POST | Run full pipeline (synthetic or live data) |
| `/api/stress-test` | POST | Run stress test scenario |
| `/api/scenarios` | GET | List available stress scenarios |
| `/api/ai/status` | GET | Check if Gemini AI is available |
| `/api/ai/summary` | POST | Generate AI executive summary |
| `/api/ai/chat` | POST | Chat about analysis results |

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

| Variable | Default | Description |
|----------|---------|-------------|
| `API_URL` | `http://localhost:9000` | Backend API URL (Next.js proxy, server-side) |
| `ALLOWED_ORIGINS` | `http://localhost:3000` | CORS allowed origins (comma-separated) |
| `API_KEY` | *(none)* | Optional API key for auth (disabled if unset) |
| `GEMINI_API_KEY` | *(none)* | Google Gemini API key for AI features |
| `REDIS_URL` | `redis://localhost:6379/0` | Redis connection URL |
| `DATABASE_URL` | *(none)* | TimescaleDB connection URL |

## Optional Dependencies

```bash
pip install -e ".[dev]"       # pytest, pytest-cov
pip install -e ".[live]"      # yfinance (live market data)
pip install -e ".[ai]"        # google-genai (Gemini AI)
pip install -e ".[dev,live,ai]"  # everything
```

## License

MIT
