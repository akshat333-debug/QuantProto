# QuantProto — Requirements (v1)

## Existing (Implemented ✅)

### Core Engine
- [x] Factor alpha engine: momentum, mean-reversion, volatility, composite signal
- [x] Walk-forward backtester with configurable train/test windows
- [x] Bootstrap Sharpe confidence intervals
- [x] HMM regime detection (3-state: BULL/NEUTRAL/BEAR)
- [x] Execution model: slippage + transaction cost simulation
- [x] Deterministic seeding on all stochastic paths

### Risk & Portfolio
- [x] Risk metrics: Sharpe, Sortino, VaR, CVaR, Beta, concentration (HHI)
- [x] Risk gate: threshold-based go/no-go decision engine
- [x] Drawdown analytics: max drawdown, Calmar, pain index, underwater periods
- [x] Portfolio optimization: Mean-Variance, Risk Parity, Max Sharpe, Black-Litterman
- [x] Correlation engine + PCA decomposition
- [x] Stress testing: 5 historical crisis scenarios + Monte Carlo simulation

### Agents & Orchestration
- [x] AlphaAgent: generates composite signals
- [x] RiskAgent: evaluates portfolio risk + gate check
- [x] Orchestrator: chains Alpha → Regime → Backtest → Risk → Decision
- [x] JWT-based A2A auth
- [x] HTTP agent server
- [x] Agent card metadata

### MCP Interface
- [x] 14 MCP tools (alpha, risk, backtest, regime)
- [x] Rate limiting (token bucket)
- [x] Input sanitization + validation
- [x] Structured logging with timing

### Dashboard
- [x] Next.js 16 frontend with 6 analysis tabs
- [x] FastAPI REST API (run-analysis, stress-test, scenarios, health)
- [x] API proxy via Next.js rewrites (no hardcoded URLs)
- [x] Dark/light theme with accessible toggle
- [x] ARIA tab pattern, labeled form inputs
- [x] Inline error banners for API failures
- [x] Input validation (client + server side)
- [x] CORS restricted to allowed origins
- [x] Optional API key auth middleware
- [x] Security headers (CSP, HSTS, X-Frame-Options)
- [x] `next/font` for Inter (no external font link)

### Infrastructure
- [x] Pre-trade compliance checks
- [x] Hash-chained audit log (tamper-evident)
- [x] Paper trading broker (PaperBroker with PnL)
- [x] Docker Compose (app + TimescaleDB + Redis)
- [x] 246 backend tests (18 test files)

### Data & ML
- [x] Synthetic data generator (seeded)
- [x] DataFetcher + UniverseManager
- [x] ML alpha models + feature store
- [x] Strategy registry (base, multi-strategy, registry pattern)

---

## Missing / Incomplete ⚠️

### High Priority
- [ ] **Root README.md** — No root README exists (only `dashboard/README.md` + `PROJECT.md`)
- [ ] **Uncommitted audit fixes** — 8 modified files + 1 new test dir not yet committed/pushed
- [ ] **Frontend component decomposition** — Entire dashboard is one 780-line monolithic `page.tsx`
- [ ] **Frontend tests** — Smoke test file exists but jest/testing-library deps not installed
- [ ] **Real data integration** — Only synthetic data; no live market data fetch from Yahoo/Alpha Vantage
- [ ] **Persistent storage** — TimescaleDB defined in Docker but no ORM/migration/query layer in code

### Medium Priority
- [ ] **GenAI features** — LLM-powered risk analysis, chat interface (planned in prior conversation)
- [ ] **CI/CD pipeline** — No GitHub Actions / CI config
- [ ] **E2E tests** — No Playwright/Cypress for dashboard flows
- [ ] **API documentation** — No Swagger/OpenAPI docs page served from dashboard
- [ ] **WebSocket dashboard cleanup** — Legacy inline HTML dashboard still exists alongside Next.js
- [ ] **Performance optimization** — No React.memo / lazy loading on heavy chart components

### Low Priority
- [ ] **Monitoring/observability** — No Prometheus/Grafana integration
- [ ] **Multi-user support** — No user sessions or auth on frontend
- [ ] **Export/download** — Can't export analysis results as PDF/CSV
- [ ] **Mobile responsiveness** — Dashboard layout not fully optimized for mobile
