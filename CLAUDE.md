# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## MCP Tools: code-review-graph

**IMPORTANT: This project has a knowledge graph. ALWAYS use the
code-review-graph MCP tools BEFORE using Grep/Glob/Read to explore
the codebase.** The graph is faster, cheaper (fewer tokens), and gives
you structural context (callers, dependents, test coverage) that file
scanning cannot.

### When to use graph tools FIRST

- **Exploring code**: `semantic_search_nodes` or `query_graph` instead of Grep
- **Understanding impact**: `get_impact_radius` instead of manually tracing imports
- **Code review**: `detect_changes` + `get_review_context` instead of reading entire files
- **Finding relationships**: `query_graph` with callers_of/callees_of/imports_of/tests_for
- **Architecture questions**: `get_architecture_overview` + `list_communities`

Fall back to Grep/Glob/Read **only** when the graph doesn't cover what you need.

### Key Tools

| Tool | Use when |
|------|----------|
| `detect_changes` | Reviewing code changes — gives risk-scored analysis |
| `get_review_context` | Need source snippets for review — token-efficient |
| `get_impact_radius` | Understanding blast radius of a change |
| `get_affected_flows` | Finding which execution paths are impacted |
| `query_graph` | Tracing callers, callees, imports, tests, dependencies |
| `semantic_search_nodes` | Finding functions/classes by name or keyword |
| `get_architecture_overview` | Understanding high-level codebase structure |
| `refactor_tool` | Planning renames, finding dead code |

### Workflow

1. The graph auto-updates on file changes (via hooks).
2. Use `detect_changes` for code review.
3. Use `get_affected_flows` to understand impact.
4. Use `query_graph` pattern="tests_for" to check coverage.

---

## Commands

### Backend

```bash
# Setup
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev,live,ai]"        # standard dev install
pip install -e ".[dev,live,ai,db]"     # + psycopg for Postgres

# Tests
pytest                                 # full suite (322 tests)
pytest tests/test_pbo.py -v            # single file
pytest -k "TestCostsWired" -v          # single class
pytest --tb=short -q                   # quiet mode

# Run demo (full pipeline, prints robustness verdict)
python -m quantproto.demo.run_demo

# Start API
uvicorn quantproto.dashboard.api:app --port 9000 --reload

# Start MCP server
python -m quantproto.mcp.server
```

### Frontend (Next.js)

```bash
cd dashboard
npm install
npm run dev          # dev server on :3000
npm run build        # production build
npx tsc --noEmit     # type check only
```

### Docker (full stack)

```bash
docker compose up -d   # API (:9000), Dashboard (:3000), TimescaleDB, Redis
```

---

## Architecture

QuantProto is a **backtest-integrity auditor** — it tells you whether a strategy's edge is real or an artefact of overfitting. The tool works on **any** backtest (bring-your-own returns from Backtrader, QuantConnect, etc.) and on the built-in research engine.

### Data flow

```
User returns / equity / trades
        │
   [ingest.py]  ──parse──►  np.ndarray
        │
   [integrity/]  ─────────►  Robustness Score (0–100)
        │                     ├─ deflated_sharpe.py   (PSR, DSR, MTRL)
        │                     ├─ pbo.py               (CSCV)
        │                     ├─ cost_sensitivity.py  (break-even bps)
        │                     └─ bias_checks.py       (red-flags)
        │
   [score.py]  ─────────►  verdict: robust / fragile / likely_overfit
```

Built-in engine pipeline (via Orchestrator):

```
fetch_prices → FactorAlphaEngine → RegimeHMM.adjust_exposure →
WalkForwardBacktester (net of cost_bps) → RiskEngine (gate) →
IntegrityAgent (gate) → decision: PROCEED / REJECT
```

### Key modules

| Module | Role |
|--------|------|
| `quantproto/integrity/` | **Flagship.** Deflated Sharpe, PBO/CSCV, purged CV, cost sweep, red-flags, Robustness Score |
| `quantproto/adapters/` | Framework adapters: `audit_backtrader`, `audit_quantconnect`, `audit_bt`, `audit_zipline`, `audit_returns` |
| `quantproto/agents/orchestrator.py` | Chains Alpha→Regime→Backtest→Risk→Integrity gates |
| `quantproto/walk_forward.py` | Rolling OOS backtest, net of `cost_bps`, returns `avg_turnover` |
| `quantproto/regime_model.py` | 3-state HMM; `adjust_exposure()` scales positions (BEAR=0.3, NEUTRAL=0.7, BULL=1.0) |
| `quantproto/factor_engine.py` | Cross-sectional composite signal; `DEFAULT_DIRECTIONS` prevents sign cancellation |
| `quantproto/risk_engine.py` | VaR, CVaR, Sharpe, Sortino, HHI + risk gate |
| `quantproto/storage/` | Hash-chained audit-run persistence (SQLite default, Postgres via `DATABASE_URL`) |
| `quantproto/mcp/server.py` | FastMCP server; exposes `robustness_audit`, `deflated_sharpe`, `prob_backtest_overfit`, `cost_sensitivity`, `probabilistic_sharpe` |
| `quantproto/dashboard/api.py` | FastAPI; `/api/run-analysis`, `/api/audit` (BYO), `/api/runs`, `/api/stress-test` |
| `dashboard/` | Next.js frontend with Integrity Audit tab + bring-your-own panel |

### Critical invariants (guarded by `tests/test_wiring.py`)

- `cost_bps > 0` must reduce returns vs `cost_bps = 0` (costs hit the backtest)
- `Orchestrator.run_pipeline()` must return `integrity` field with `score` key
- `regime_aware=True` must produce different equity curve than `regime_aware=False`

These tests exist to prevent regressions to the original "decorative" state (features computed but never wired into decisions).

### Environment variables

| Variable | Default | Description |
|----------|---------|-------------|
| `DATABASE_URL` | SQLite at `~/.quantproto/audit.db` | Postgres/TimescaleDB for audit runs |
| `REDIS_URL` | in-memory | Redis for distributed rate limiting |
| `GEMINI_API_KEY` | mock fallback | AI-powered analysis summaries |
| `ALLOWED_ORIGINS` | `http://localhost:3000` | CORS origins |
| `API_KEY` | disabled | Optional API-key auth |

### BYO audit surface

The `/api/audit` endpoint and `POST`-able `IntegrityTab` in the frontend accept:
- `returns`: list of daily return floats
- `equity`: list of equity curve values (converted internally)
- `trades`: list of P&L values + `capital`
- Optional `variant_matrix` (T×N array of all configs tried) for PBO

Without `variant_matrix`, PBO is unavailable but DSR + cost-sensitivity + red-flags still run.

### Scoring weights (Robustness Score)

| Component | Weight | Source |
|-----------|--------|--------|
| Significance (DSR or PSR) | 35% | Uses DSR when variant_matrix provided — prevents overfit strategies from scoring high on in-sample PSR |
| Selection (PBO) | 30% | Skipped when variant_matrix absent |
| Cost survival | 20% | Full credit when edge survives ≥30 bps |
| Sample adequacy | 15% | Based on minimum track record length |

Red-flag penalties: high=12pts, medium=5pts, low=2pts.
