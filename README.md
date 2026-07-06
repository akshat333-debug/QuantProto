# QuantProto

> **The backtest-integrity auditor.** Paste any strategy's returns and find out whether its edge is real or an artefact of overfitting — Deflated Sharpe, Probability of Backtest Overfitting, cost break-even, and bias red-flags, distilled into one Robustness Score. Exposed as MCP tools so agents can audit strategies too.

[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://python.org)
[![Tests](https://img.shields.io/badge/tests-396%20passing-brightgreen.svg)]()
[![CI](https://img.shields.io/github/actions/workflow/status/akshat333-debug/QuantProto/ci.yml?label=CI)](https://github.com/akshat333-debug/QuantProto/actions)

---

## Why this exists

Every survey of quant practitioners says the same thing: **the #1 thing that kills strategies is overfitting** — backtests inflated by lookahead bias, survivorship bias, and ignored transaction costs. A single one-bar lookahead can turn a losing strategy into an apparent Sharpe‑3 winner.

Yet the popular tools — Backtrader, QuantConnect, no-code signal builders — are *optimisers*. They make it trivially easy to curve-fit and hand you a beautiful equity curve with no warning. The rigorous defences exist (the **Deflated Sharpe Ratio** and **Probability of Backtest Overfitting** from Bailey & López de Prado, purged cross-validation) but they live in papers and a couple of obscure libraries — **not in the tools people actually use.**

QuantProto closes that gap. It is not another backtester. It is the layer that sits *on top of* your backtest and tells you the truth about it.

## What it does

**Bring your own backtest.** Built it in Backtrader, QuantConnect, Excel, or a notebook? Paste the return series (or equity curve, or trade P&Ls) and get:

| Check | Question it answers |
|-------|---------------------|
| **Probabilistic Sharpe Ratio** | Is the Sharpe statistically real given sample length, skew, and fat tails? |
| **Deflated Sharpe Ratio** | After trying N configurations, is the best one's Sharpe just luck? |
| **Probability of Backtest Overfitting** (CSCV) | Does the in-sample winner generalise out-of-sample, or was it cherry-picked? |
| **Cost break-even** | At what transaction cost (bps) does the edge die? |
| **Bias red-flags** | Implausible Sharpe, suspiciously smooth equity, too-short sample, fat tails |
| **Robustness Score (0–100)** | One honest verdict: **robust** / **fragile** / **likely overfit** |

Plus an explicit **manual checklist** for the biases that *cannot* be detected from returns alone (survivorship, lookahead, point-in-time data) — because pretending otherwise would be dishonest.

## Quick start — audit a backtest

```bash
pip install -e ".[dev]"
```

**From Backtrader:**
```python
import backtrader as bt
from quantproto.adapters import audit_backtrader

cerebro = bt.Cerebro()
cerebro.addstrategy(MyStrategy)
cerebro.addanalyzer(bt.analyzers.TimeReturn, _name="time_return")
result = cerebro.run()

report = audit_backtrader(result, n_trials=50)
print(report["score"], report["verdict"])   # e.g. 38.0  likely_overfit
```

**From QuantConnect** (paste your JSON download):
```python
import json
from quantproto.adapters import audit_quantconnect

result = json.load(open("backtest.json"))
report = audit_quantconnect(result, n_trials=50)
print(report["statistics"]["breakeven_bps"])    # edge dies above N bps
```

**From zipline / bt / any equity curve:**
```python
from quantproto.adapters import audit_zipline, audit_bt, audit_returns

report = audit_zipline(perf)          # zipline perf DataFrame
report = audit_bt(bt_result)          # bt.Result object
report = audit_returns(my_returns)    # plain list / Series / ndarray
```

**Low-level (full control):**
```python
from quantproto.integrity import robustness_report

report = robustness_report(my_returns, n_trials=50, turnover=0.3)
print(report["score"], report["verdict"])
for flag in report["red_flags"]:
    print(flag["severity"], flag["message"])
```

To also compute the Probability of Backtest Overfitting, pass the returns of **every** configuration you tried (not just the winner):

```python
report = robustness_report(best_variant_returns, variant_matrix=all_variants)
print(report["pbo"]["pbo"])   # 0.0 = generalises, 1.0 = pure overfit
```

## Experiment tracker — the honest trial count

Deflated Sharpe and PBO both need one input nobody actually has: **how many
configurations were really tried.** The tracker removes the guesswork by
logging every run as you search, so `n_trials` and the variant matrix build
themselves — a Weights & Biases for backtests.

```python
import quantproto as qp

exp = qp.experiment("spy-meanrev")
with exp.run(params={"lookback": 20, "stop": 0.02}) as run:
    stats = my_backtest(lookback=20, stop=0.02)
    run.log_returns(stats.daily_returns)

exp.status()               # research-budget meter: DSR/PBO from *observed* trials
exp.sensitivity("lookback")  # Sharpe vs. parameter value, neighbour degradation
exp.drift()                 # live-vs-backtest PSR check once you're trading it
```

CLI (console script `qp`):

```bash
qp list                      # experiments + run counts
qp status <experiment>       # research-budget meter
qp runs <experiment>          # run table (ts, params, sharpe)
qp report <experiment>       # full robustness audit of the best run
qp sensitivity <exp> <param> # parameter-sensitivity check
qp drift <experiment>        # live-vs-backtest divergence (consistent/watch/diverging)
qp certificate <experiment>  # shareable, tamper-evident HTML provenance certificate
qp verify <experiment>       # hash-chain intact?
```

The ledger is hash-chained (SQLite at `~/.quantproto/experiments.db` by
default, override with `QUANTPROTO_LEDGER`; Postgres via `DATABASE_URL`) —
so the trial count in the budget meter and the provenance certificate is
tamper-evident, not self-reported. See [docs/tracker-design.md](docs/tracker-design.md)
for the full design.

## Agent-callable (MCP)

The whole auditor is exposed as MCP tools, so an AI agent can audit a strategy as part of a workflow:

| Tool | What it does |
|------|-------------|
| `robustness_audit` | Full overfitting audit → Robustness Score + verdict |
| `prob_backtest_overfit` | PBO via CSCV over a strategy-variant matrix |
| `deflated_sharpe` / `probabilistic_sharpe` | Multiple-testing & non-normality corrected Sharpe |
| `cost_sensitivity` | Net Sharpe across a cost grid + break-even bps |
| `log_run` / `research_budget` / `experiment_report` | Experiment tracker: log a trial, get the budget meter, full audit of the best run |
| `log_live` / `live_drift` | Log live fills against a tracked experiment; PSR-test live vs. backtest divergence |

Run the server: `python -m quantproto.mcp.server`. All tools include rate limiting (Redis-backed when `REDIS_URL` is set) and input sanitisation.

## The built-in research engine (optional)

QuantProto also ships a small, **honest** end-to-end quant pipeline that the auditor watches over — useful as a reference for what a correctly-wired research loop looks like:

1. **Alpha signal** — composite of momentum, mean-reversion, volatility (cross-sectional ranking, direction-corrected so factors don't cancel)
2. **Regime detection** — 3-state HMM that **actually scales exposure** before execution (fit only on history available at each rebalance — no lookahead)
3. **Walk-forward backtest** — rolling out-of-sample, **net of transaction costs**, with bootstrap Sharpe CIs
4. **Risk gate** — VaR / CVaR / Sharpe / concentration thresholds
5. **Integrity gate** — the Robustness Score; the pipeline **rejects an overfit backtest even if alpha and risk look great**

```bash
python -m quantproto.demo.run_demo   # deterministic, seeded; prints the robustness verdict
```

> Every component shown is wired into the decision. (An earlier version computed regime, costs, and alpha for display but never fed them into the backtest — that gap is now closed and guarded by `tests/test_wiring.py`.)

### Dashboard

```bash
uvicorn quantproto.dashboard.api:app --port 9000 --reload   # API
cd dashboard && npm install && npm run dev                  # UI on :3000
```

The **Integrity Audit** tab renders the Robustness Score, PBO, cost-sensitivity curve, and red-flags — and includes a paste-your-own-backtest panel that needs no engine run. Live Yahoo Finance data **fails loudly** rather than silently substituting synthetic prices.

### Docker (full stack)

```bash
docker compose up -d   # API (:9000), Dashboard (:3000), TimescaleDB, Redis
```

Audit runs are persisted (hash-chained, tamper-evident) to Postgres/TimescaleDB when `DATABASE_URL` is set, else a local SQLite file — so results are reproducible and queryable (`GET /api/runs`). Every run also has a **shareable permalink**: `GET /api/runs/{id}/report` renders a self-contained HTML robustness report you can send to a PM or allocator — no dashboard required (there's an "Open shareable report" link on every audit). Rate limiting uses Redis when `REDIS_URL` is set.

## Deploy

**Live:** dashboard at [quantproto.vercel.app](https://quantproto.vercel.app), API at
[quantproto-production.up.railway.app](https://quantproto-production.up.railway.app).

See [DEPLOY.md](DEPLOY.md) for the full step-by-step guide.

**TL;DR (5 minutes):**
1. Deploy the API to Railway: `railway init && railway up`
2. Set `ALLOWED_ORIGINS` to your Vercel URL in Railway
3. Import the repo to Vercel, set root dir = `dashboard`, add env var `API_URL=<railway-url>`
4. Done — anyone can paste returns and get a Robustness Score without installing anything

## Project structure

```
quantproto/
├── integrity/         # ★ the auditor: deflated_sharpe, pbo, purged_cv,
│                      #   cost_sensitivity, bias_checks, score, ingest (BYO)
├── adapters/          # Framework adapters: Backtrader, QuantConnect, bt, zipline
├── agents/            # AlphaAgent, RiskAgent, IntegrityAgent, Orchestrator (JWT A2A)
├── mcp/               # FastMCP server — agent-callable tools + rate limiting
├── factor_engine.py   # Factor alpha (direction-aware composite)
├── risk_engine.py     # VaR, CVaR, Sharpe, Sortino, Beta, HHI + risk gate
├── regime_model.py    # HMM regime detection + exposure scaling (now wired in)
├── walk_forward.py    # Walk-forward backtester (cost-aware) + bootstrap CI
├── execution_model.py # Transaction-cost / slippage model (drives backtest costs)
├── storage/           # Durable, hash-chained audit-run store (SQLite/Postgres)
├── tracker/           # Experiment tracker: hash-chained run ledger, research-budget
│                      #   meter, sensitivity, live-drift monitor, provenance certificate
├── analytics/ portfolio/ risk/ compliance/ data/ strategy/ trading/
└── dashboard/         # FastAPI REST API (run-analysis, audit, runs, experiments, AI summaries)

dashboard/             # Next.js frontend (Integrity tab + Experiments tab + bring-your-own auditor)
tests/                 # 396 tests
```

## Testing

```bash
pytest                                 # full suite (396)
pytest tests/test_pbo.py               # overfitting detection
pytest tests/test_deflated_sharpe.py   # DSR / PSR statistics
pytest tests/test_wiring.py            # guards: components stay connected
pytest tests/test_adapters.py          # Backtrader / QC / bt / zipline adapters
pytest tests/test_tracker*.py          # ledger, budget meter, drift, certificate
```

The integrity tests are property-based: synthetic overfit data must score `likely_overfit` and yield high PBO; a genuine edge must score `robust` with low PBO; purged folds must have zero leakage.

## Environment variables

| Variable | Description |
|----------|-------------|
| `DATABASE_URL` | Postgres/TimescaleDB for audit-run and experiment-tracker persistence (default: local SQLite) |
| `QUANTPROTO_LEDGER` | Override path for the experiment tracker's SQLite ledger (default `~/.quantproto/experiments.db`) |
| `REDIS_URL` | Redis for distributed rate limiting (default: in-memory) |
| `GEMINI_API_KEY` | Optional — AI-powered analysis summaries (mock fallback otherwise) |
| `ALLOWED_ORIGINS` | CORS origins for the API (default `http://localhost:3000`) |
| `API_KEY` | Optional API-key auth (disabled if unset) |

## License

MIT
