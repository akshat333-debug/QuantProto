# QuantProto — Roadmap

## Completed

### Backtest-Integrity Auditor ✅ (the flagship)
- Probabilistic & Deflated Sharpe Ratio (sample length, non-normality, multiple-testing)
- Probability of Backtest Overfitting via CSCV
- Purged & embargoed K-fold cross-validation (leak-free OOS)
- Transaction-cost sensitivity sweep + break-even bps
- Statistical red-flag detection + manual integrity checklist
- Robustness Score (0–100) with robust / fragile / likely-overfit verdict
- Bring-your-own-backtest ingestion (returns / equity / trades / variant matrix)

### Engine — fully wired & honest ✅
- Walk-forward backtester now **net of transaction costs**
- HMM regime detection now **actually scales exposure** (no lookahead)
- Composite signal direction-corrected (factors no longer cancel)
- Live data **fails loud** instead of silently faking it
- Integrity gate folded into the orchestrator decision
- Regression tests guarantee components stay connected (`test_wiring.py`)

### Protocol Layer ✅
- Integrity audit exposed as MCP tools (`robustness_audit`, `prob_backtest_overfit`, …)
- A2A agent trio: Alpha → Risk → **Integrity** → Orchestrator (JWT auth)
- Deterministic seeding on all stochastic paths

### Infrastructure ✅
- Durable, hash-chained audit-run store (SQLite default, Postgres/TimescaleDB via `DATABASE_URL`)
- Redis-backed rate limiting (in-memory fallback)
- Next.js dashboard: Integrity Audit tab + bring-your-own panel
- Full UI redesign: sidebar layout, deep-navy design system, score ring, JetBrains Mono data typography (Stitch reference in `docs/design/`)
- GitHub Actions CI (Python 3.11+3.12, Node 22) + Docker stack
- 358 backend tests
- Shareable audit-run permalinks (`GET /api/runs/{id}/report` → self-contained HTML report)

### Framework Adapters ✅
- Backtrader: `audit_backtrader(cerebro.run(), n_trials=N)` — reads `TimeReturn` analyzer or accepts an equity series
- QuantConnect: `audit_quantconnect(result_json)` — parses Charts → Strategy Equity → Values path
- bt (Pmorales): `audit_bt(bt_result)` — reads `.prices` DataFrame
- zipline / zipline-reloaded: `audit_zipline(perf)` — reads `returns` or `portfolio_value` column
- `audit_returns()` for plain lists / Series / ndarrays from any source

### Deployment ✅
- Vercel config (`vercel.json`) for the Next.js frontend
- Railway config (`railway.json`) + Fly.io config (`fly.toml`) for the FastAPI backend
- Step-by-step guide (`DEPLOY.md`) covering Railway + Vercel in 5 minutes

---

## Next

- [ ] Combinatorial Purged CV (CPCV) for tighter PBO estimates
- [ ] Haircut Sharpe (Harvey–Liu) alongside the Deflated Sharpe
- [ ] Playwright E2E tests for the dashboard
- [ ] Alert webhooks when a saved strategy's robustness degrades
