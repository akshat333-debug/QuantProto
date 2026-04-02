# QuantProto — Roadmap

## Completed

### Core Engine ✅
- Walk-forward backtester with bootstrap Sharpe CI
- HMM regime detection (3-state: Bull/Neutral/Bear)
- Factor alpha engine (momentum, mean-reversion, volatility, composite)
- Risk gate system (VaR, Sharpe, concentration thresholds)
- Execution model (slippage + transaction costs)
- 246 backend tests

### Protocol Layer ✅
- MCP tool interface via FastMCP (rate limiting, input sanitization)
- A2A agent trio (AlphaAgent → RiskAgent → Orchestrator)
- JWT-based agent authentication
- Deterministic seeding on all stochastic paths

### Infrastructure ✅
- Dashboard decomposition (modular components)
- Live market data (yfinance + CSV cache + synthetic fallback)
- GitHub Actions CI (Python 3.11+3.12, Node 22)
- Docker production builds (API + Dashboard + TimescaleDB + Redis)

---

## Deferred

- [ ] Playwright E2E tests
- [ ] Database migration layer (Alembic + SQLAlchemy)
- [ ] Ticker autocomplete against known universe
- [ ] Alert webhooks on risk gate violations
