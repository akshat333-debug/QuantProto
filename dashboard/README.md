# QuantProto Dashboard

Next.js 16 frontend for the QuantProto quantitative research engine.

## Features

- **Six analysis tabs**: Overview, Performance, Risk, Regime, Portfolio, Stress Test
- **Live market data**: Yahoo Finance integration with date range picker (synthetic fallback)
- **Strategy builder**: Interactive factor weight sliders (momentum, mean-reversion, volatility)
- **AI analysis**: Gemini-powered executive summaries + floating chat panel
- **Data export**: Download results as CSV or JSON
- **Portfolio optimization**: Mean-Variance, Risk Parity, Max Sharpe visualizations
- **Stress testing**: Monte Carlo simulation & historical crisis scenarios
- **Dark/Light mode**: System-aware theme switching
- **Mobile responsive**: Optimized for all screen sizes
- **Accessible**: ARIA tab navigation, labeled inputs, keyboard support

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

## Component Architecture

```
src/
├── app/page.tsx                    # Slim orchestrator (~200 lines)
├── components/
│   ├── tabs/
│   │   ├── OverviewTab.tsx         # AI summary + metrics + equity curve + asset table
│   │   ├── PerformanceTab.tsx      # Full equity + drawdown charts
│   │   ├── RiskTab.tsx             # Correlation matrix + PCA + gate violations
│   │   ├── RegimeTab.tsx           # Regime timeline + confidence + distribution
│   │   ├── PortfolioTab.tsx        # Allocation pie charts + comparison bar
│   │   └── StressTestTab.tsx       # Crisis scenarios + Monte Carlo paths
│   └── ui/
│       ├── AISummary.tsx           # Collapsible AI executive summary panel
│       ├── ChatPanel.tsx           # Floating AI chat widget
│       ├── ChartTooltip.tsx        # Custom Recharts tooltip
│       ├── DecisionBadge.tsx       # Pass/fail decision indicator
│       ├── ErrorBanner.tsx         # Dismissible error banner
│       ├── ExportPanel.tsx         # CSV + JSON download buttons
│       ├── MetricCard.tsx          # Stat display card
│       ├── StrategyBuilder.tsx     # Factor weight sliders
│       └── ThemeToggle.tsx         # Dark/light theme switch
└── lib/
    ├── api.ts                      # API client functions
    └── types.ts                    # Shared TypeScript types
```

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `API_URL` | `http://localhost:9000` | Backend API URL (used by Next.js rewrites, server-side only) |

## Build for Production

```bash
npm run build     # Standalone output for Docker
npm start         # Start production server
```

## Docker

```bash
docker build -t quantproto-dashboard .
docker run -p 3000:3000 -e API_URL=http://api:9000 quantproto-dashboard
```

## Tech Stack

- **Framework**: Next.js 16 (App Router, standalone output)
- **Charts**: Recharts
- **Styling**: Tailwind CSS 4
- **Icons**: Lucide React
- **Typography**: Inter (via `next/font`)
