# QuantProto Dashboard

Next.js frontend for the QuantProto quantitative research engine.

## Features

- **Six analysis tabs**: Overview, Performance, Risk, Regime, Portfolio, Stress Test
- **Real-time analysis**: Walk-forward backtesting, factor signals, regime detection
- **Portfolio optimization**: Mean-Variance, Risk Parity, Max Sharpe visualizations
- **Stress testing**: Monte Carlo simulation & historical crisis scenarios
- **Dark/Light mode**: System-aware theme switching via `next-themes`

## Quick Start

### 1. Start the API server

```bash
cd ..
uvicorn quantproto.dashboard.api:app --host 0.0.0.0 --port 9000 --reload
```

### 2. Start the dashboard

```bash
npm install
npm run dev
```

Open [http://localhost:3000](http://localhost:3000).

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `API_URL` | `http://localhost:9000` | Backend API URL (used by Next.js rewrites, server-side only) |

See [`.env.example`](.env.example) for a documented template.

## Build for Production

```bash
npm run build
npm start
```

## Tech Stack

- **Framework**: Next.js 16 (App Router)
- **Charts**: Recharts
- **Styling**: Tailwind CSS 4
- **Icons**: Lucide React
- **Typography**: Inter (via `next/font`)
