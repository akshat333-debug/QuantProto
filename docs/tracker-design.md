# QuantProto Tracker — design

## Why

Market research (July 2026, see memory `pivot-market-research`): the field's #1 recurring
question is "how do I know I've overfit?", and the honest statistics that answer it
(Deflated Sharpe, PBO) require the one input nobody has — **how many configurations were
actually tried**. Practitioners undercount their trials 5–10x because nothing records
their runs. Competing products (AuditZK) verify *live* track records or offer static
form calculators with self-reported trial counts; no product captures the research
process itself.

The tracker flips QuantProto from "paste returns, get a score" to
**"we watched your whole search, here is the honest verdict"** — a Weights & Biases
for backtests where the variant matrix builds itself.

## User-facing API

```python
import quantproto as qp

exp = qp.experiment("spy-meanrev")               # open/create ledger entry

# Style 1 — context manager per run
with exp.run(params={"lookback": 20, "stop": 0.02}) as run:
    stats = my_backtest(lookback=20, stop=0.02)
    run.log_returns(stats.daily_returns)         # or run.log_equity(equity_curve)

# Style 2 — one-liner
exp.log(returns, params={"lookback": 50, "stop": 0.02})

# Style 3 — framework hook (backtesting.py)
bt = Backtest(data, MyStrategy, cash=10_000)
stats = exp.capture_backtesting(bt, lookback=20)  # runs bt.run(**kwargs), logs equity + params

exp.status()        # research-budget meter (see below)
exp.report()        # full robustness_report of best run, variant matrix auto-built
exp.sensitivity("lookback")   # Sharpe vs parameter value, neighbour degradation
exp.verify()        # hash-chain intact?
```

CLI (console script `qp`):

```
qp list                      # experiments + run counts
qp status <experiment>       # budget meter
qp runs <experiment>         # run table (ts, params, sharpe)
qp report <experiment>       # full audit of best run
qp verify <experiment>       # tamper check
```

## Research-budget meter (`exp.status()`)

Computed from **all logged runs** of the experiment — the user never supplies
`n_trials` or `variant_matrix` again:

| Field | Meaning |
|-------|---------|
| `n_runs` | trials burned (the honest N) |
| `best_sharpe_ann` | best annualized Sharpe so far |
| `spurious_sharpe_ann` | expected max annualized Sharpe from N trials of pure noise (`expected_max_sharpe`, var inferred across runs; √(2·lnN)/√T fallback) |
| `dsr` | Deflated Sharpe prob of best run given the search |
| `pbo` | CSCV probability of backtest overfitting (runs aligned to common T; needs ≥ 8 runs) |
| `haircut_sharpe_ann` | best − spurious: what to actually expect OOS |
| `budget_state` | `ok` / `warning` / `burned` |
| `message` | plain English, e.g. "82 configs tried — any Sharpe below 1.31 is indistinguishable from noise. Your best is 1.24: keep the dataset, change the thesis." |

State thresholds: `burned` when best ≤ spurious or DSR < 0.5; `warning` when
DSR < 0.95 or PBO > 0.5; else `ok`.

## Ledger

Separate from `AuditStore` (that stores *audit reports*; this stores *raw research
runs*). SQLite at `~/.quantproto/experiments.db`, override with `QUANTPROTO_LEDGER`
env or `qp.experiment(name, ledger_path=...)`. Postgres backend = phase 2.

```sql
CREATE TABLE experiments (
    name        TEXT PRIMARY KEY,
    created_ts  TEXT NOT NULL,
    meta        TEXT NOT NULL         -- json
);
CREATE TABLE runs (
    id          TEXT PRIMARY KEY,
    experiment  TEXT NOT NULL,
    seq         INTEGER NOT NULL,     -- per-experiment ordinal
    ts          TEXT NOT NULL,
    params      TEXT NOT NULL,        -- json
    params_hash TEXT NOT NULL,
    source      TEXT NOT NULL,        -- manual | backtesting | vectorbt | ...
    code_hash   TEXT,                 -- sha256 of strategy source when available
    n_obs       INTEGER NOT NULL,
    sharpe      REAL NOT NULL,        -- per-period, convenience column
    returns     TEXT NOT NULL,        -- json array of per-period returns
    prev_hash   TEXT NOT NULL,
    hash        TEXT NOT NULL
);
```

Hash chain is **per experiment** (`prev_hash` = previous run's `hash` in the same
experiment, genesis otherwise), same fold-in scheme as `AuditStore`. The chain is what
turns the ledger into a provenance certificate: "all N trials logged, order intact,
N is honest."

Duplicate configs (same `params_hash`) are logged as separate runs — re-running the
same config is still a trial; the budget engine counts *distinct* configs for N
(re-runs of an identical config don't mine new noise) but keeps every row for
provenance.

## Budget math

- Per-period Sharpe per run stored at log time.
- `n_trials` = distinct `params_hash` count.
- `var_sharpe` = variance of per-period Sharpe across distinct configs (best run per
  config); needs ≥ 2 configs, else DSR unavailable → PSR only.
- Variant matrix for PBO: last `T_min` observations of each distinct config's most
  recent run, where `T_min` = shortest run length; built only when ≥ 8 configs and
  `T_min` ≥ 2 × `n_splits`. Fed into existing `pbo_cscv`.
- `exp.report()` = existing `robustness_report(best_returns, n_trials=…,
  variant_matrix=auto, …)` — full reuse of the integrity engine.

## Sensitivity (`exp.sensitivity(param)`)

Groups distinct configs by the value of one parameter (all other params equal to the
best run's values where possible, else pooled), sorts numerically, reports Sharpe per
value and `neighbour_ratio` = best neighbour Sharpe / peak Sharpe. Low ratio =
the community's "RSI 14 works, 13/15 don't" red flag, quantified.

## Phases

1. **Done**: `quantproto/tracker/` (ledger, budget, experiment API,
   backtesting.py + vectorbt capture helpers), `qp` CLI, exports, tests.
2. **Done**: Dashboard experiments tab reading the ledger; budget meter
   component; `/api/experiments*` endpoints. MCP tools: `research_budget`,
   `log_run`, `experiment_report` — audit gate for AI-generated strategies.
3. **Done**: Live-drift monitor, Postgres ledger backend, shareable
   provenance certificate, deeper framework hooks (below).

### Phase 3 detail

- **Postgres ledger backend** (`quantproto/tracker/ledger.py`): same
  `DATABASE_URL` + `psycopg` auto-detection as `AuditStore`, graceful
  fallback to SQLite on any connection failure. Own `experiments`/`runs`
  tables — can share a database with `AuditStore` without collision.
- **Live-drift monitor** (`quantproto/tracker/drift.py`): `exp.log_live(returns,
  params)` records live fills with `source="live"`, deliberately excluded
  from `_distinct_configs` (a live run is the deployed config's track record,
  not a new variant — mixing it into the search would corrupt DSR/PBO).
  `exp.drift()` runs a two-sample PSR test: P(true live Sharpe ≥ backtest
  Sharpe | live sample). States: `no_backtest` / `no_live_data` /
  `insufficient_data` (< `MIN_LIVE_OBS` = 20) / `consistent` / `watch` /
  `diverging`. Exposed via MCP (`log_live`, `live_drift`), API
  (`POST/GET .../live`, `GET .../drift`), CLI (`qp drift`).
- **Provenance certificate** (`quantproto/tracker/certificate.py`):
  `render_certificate_html(exp.report())` — reuses the score/stats/PBO/flags
  rendering from `dashboard/report_html.py` and adds a provenance block (runs
  logged, distinct configs, chain-intact badge). This is the artifact that
  answers what allocators say they can't verify: an honest, tamper-evident
  trial count. `qp certificate`, `GET /api/experiments/{name}/certificate`.
- **Deeper framework hooks**: `exp.capture_zipline(perf)` and
  `exp.capture_bt(result)` reuse the existing extraction logic from
  `quantproto/adapters/zipline.py` / `adapters/bt.py` rather than
  duplicating it — one parser, two consumers (one-shot audit vs. tracked
  search).
