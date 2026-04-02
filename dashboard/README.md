# QuantProto Dashboard

Optional visualization layer for exploring analysis results from the QuantProto engine.

## Setup

```bash
# Start the API server first
cd .. && uvicorn quantproto.dashboard.api:app --host 0.0.0.0 --port 9000 --reload

# Start the dashboard
npm install && npm run dev
```

Open [http://localhost:3000](http://localhost:3000).

## What It Shows

| Tab | Pipeline Stage |
|-----|---------------|
| **Overview** | Summary metrics, risk gate decision, equity curve |
| **Performance** | Equity curve + drawdown from walk-forward backtest |
| **Risk** | Correlation matrix, PCA, risk gate violations |
| **Regime** | HMM regime states + posterior confidence |
| **Portfolio** | Optimisation weights (MV, Risk Parity, Max Sharpe) |
| **Stress Test** | Historical crisis scenarios + Monte Carlo paths |

## Tech Stack

Next.js 16 (App Router) · Recharts · Tailwind CSS 4 · Lucide · `next/font` Inter

## Environment

| Variable | Default | Description |
|----------|---------|-------------|
| `API_URL` | `http://localhost:9000` | Backend API URL (Next.js proxy) |
