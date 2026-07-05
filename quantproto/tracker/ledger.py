"""Hash-chained ledger of backtest runs.

Distinct from :class:`quantproto.storage.AuditStore`: that persists finished
*audit reports*; this records the raw *research process* — every configuration
tried, in order, tamper-evident. The chain is what lets a report later claim
"N trials, honestly counted".

Backend, chosen automatically like ``AuditStore``:
- ``DATABASE_URL=postgresql://…`` + ``psycopg`` installed → Postgres/TimescaleDB
  (shares the database with ``AuditStore`` but uses its own tables)
- otherwise → a local SQLite file (``~/.quantproto/experiments.db``, override
  with ``QUANTPROTO_LEDGER``)
"""

from __future__ import annotations

import hashlib
import json
import logging
import os
import sqlite3
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np

DEFAULT_LEDGER_PATH = Path.home() / ".quantproto" / "experiments.db"

_SCHEMA = """
CREATE TABLE IF NOT EXISTS experiments (
    name        TEXT PRIMARY KEY,
    created_ts  TEXT NOT NULL,
    meta        TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS runs (
    id          TEXT PRIMARY KEY,
    experiment  TEXT NOT NULL,
    seq         INTEGER NOT NULL,
    ts          TEXT NOT NULL,
    params      TEXT NOT NULL,
    params_hash TEXT NOT NULL,
    source      TEXT NOT NULL,
    code_hash   TEXT,
    n_obs       INTEGER NOT NULL,
    sharpe      REAL NOT NULL,
    returns     TEXT NOT NULL,
    prev_hash   TEXT NOT NULL,
    hash        TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_runs_experiment ON runs (experiment, seq);
"""


def _hash_payload(payload: dict) -> str:
    raw = json.dumps(payload, sort_keys=True, default=str)
    return hashlib.sha256(raw.encode()).hexdigest()


def _per_period_sharpe(returns: np.ndarray) -> float:
    std = np.std(returns, ddof=1) if returns.size > 1 else 0.0
    return 0.0 if std < 1e-12 else float(np.mean(returns) / std)


class RunLedger:
    """Persist and query hash-chained experiment runs."""

    def __init__(self, path: str | os.PathLike | None = None, url: str | None = None):
        self.url = url if url is not None else os.getenv("DATABASE_URL")
        self._pg = False
        env_path = os.getenv("QUANTPROTO_LEDGER")
        self.path = (
            Path(path) if path is not None else Path(env_path) if env_path else DEFAULT_LEDGER_PATH
        )
        self._conn = self._connect()
        self._init_schema()

    # ── Backend selection (mirrors quantproto.storage.AuditStore) ─────────
    def _connect(self):
        if self.url and self.url.startswith(("postgres://", "postgresql://")):
            try:
                import psycopg  # type: ignore

                self._pg = True
                return psycopg.connect(self.url)
            except Exception as e:  # psycopg missing or connection failed
                logging.getLogger("quantproto.tracker").warning(
                    "Postgres unavailable (%s); falling back to SQLite.", e
                )
                self._pg = False
        self.path.parent.mkdir(parents=True, exist_ok=True)
        return sqlite3.connect(str(self.path), check_same_thread=False)

    @property
    def backend(self) -> str:
        return "postgres" if self._pg else "sqlite"

    def _ph(self) -> str:
        return "%s" if self._pg else "?"

    def _init_schema(self) -> None:
        cur = self._conn.cursor()
        if self._pg:
            for stmt in _SCHEMA.strip().split(";"):
                stmt = stmt.strip()
                if stmt:
                    cur.execute(stmt)
        else:
            self._conn.executescript(_SCHEMA)
        self._conn.commit()

    # ── Experiments ───────────────────────────────────────────────────────
    def ensure_experiment(self, name: str, meta: dict | None = None) -> None:
        ph = self._ph()
        cur = self._conn.cursor()
        cur.execute(f"SELECT 1 FROM experiments WHERE name = {ph}", (name,))
        if cur.fetchone() is None:
            cur.execute(
                f"INSERT INTO experiments (name, created_ts, meta) VALUES ({ph}, {ph}, {ph})",
                (name, datetime.now(timezone.utc).isoformat(), json.dumps(meta or {})),
            )
            self._conn.commit()

    def list_experiments(self) -> list[dict]:
        cur = self._conn.cursor()
        cur.execute(
            "SELECT e.name, e.created_ts, COUNT(r.id) FROM experiments e "
            "LEFT JOIN runs r ON r.experiment = e.name "
            "GROUP BY e.name, e.created_ts ORDER BY e.created_ts DESC"
        )
        return [
            {"name": n, "created_ts": ts, "n_runs": c} for n, ts, c in cur.fetchall()
        ]

    # ── Runs ──────────────────────────────────────────────────────────────
    def _tail(self, experiment: str) -> tuple[int, str]:
        """(last seq, last hash) for an experiment's chain."""
        ph = self._ph()
        cur = self._conn.cursor()
        cur.execute(
            f"SELECT seq, hash FROM runs WHERE experiment = {ph} ORDER BY seq DESC LIMIT 1",
            (experiment,),
        )
        row = cur.fetchone()
        return (row[0], row[1]) if row else (0, "genesis")

    def record_run(
        self,
        experiment: str,
        returns: np.ndarray,
        params: dict[str, Any],
        source: str = "manual",
        code_hash: str | None = None,
    ) -> dict:
        """Append one run to the experiment's chain; returns id + chain hash."""
        r = np.asarray(returns, dtype=float)
        if r.ndim != 1 or r.size < 2:
            raise ValueError("returns must be a 1-D series with at least 2 observations")
        if not np.all(np.isfinite(r)):
            raise ValueError("returns contain NaN or infinite values")

        self.ensure_experiment(experiment)
        run_id = uuid.uuid4().hex
        ts = datetime.now(timezone.utc).isoformat()
        seq, prev = self._tail(experiment)
        seq += 1
        params_json = json.dumps(params, sort_keys=True, default=str)
        params_hash = hashlib.sha256(params_json.encode()).hexdigest()
        returns_json = json.dumps([float(x) for x in r])
        chain_hash = _hash_payload(
            {
                "id": run_id,
                "experiment": experiment,
                "seq": seq,
                "ts": ts,
                "params_hash": params_hash,
                "returns_sha": hashlib.sha256(returns_json.encode()).hexdigest(),
                "prev": prev,
            }
        )
        ph = self._ph()
        self._conn.cursor().execute(
            f"INSERT INTO runs (id, experiment, seq, ts, params, params_hash, source, "
            f"code_hash, n_obs, sharpe, returns, prev_hash, hash) "
            f"VALUES ({ph},{ph},{ph},{ph},{ph},{ph},{ph},{ph},{ph},{ph},{ph},{ph},{ph})",
            (
                run_id, experiment, seq, ts, params_json, params_hash, source,
                code_hash, int(r.size), _per_period_sharpe(r), returns_json,
                prev, chain_hash,
            ),
        )
        self._conn.commit()
        return {"id": run_id, "seq": seq, "ts": ts, "hash": chain_hash}

    def list_runs(self, experiment: str, with_returns: bool = False) -> list[dict]:
        cols = "id, seq, ts, params, params_hash, source, code_hash, n_obs, sharpe"
        if with_returns:
            cols += ", returns"
        ph = self._ph()
        cur = self._conn.cursor()
        cur.execute(
            f"SELECT {cols} FROM runs WHERE experiment = {ph} ORDER BY seq ASC",
            (experiment,),
        )
        out = []
        for row in cur.fetchall():
            rec = {
                "id": row[0], "seq": row[1], "ts": row[2],
                "params": json.loads(row[3]), "params_hash": row[4],
                "source": row[5], "code_hash": row[6],
                "n_obs": row[7], "sharpe": row[8],
            }
            if with_returns:
                rec["returns"] = np.asarray(json.loads(row[9]), dtype=float)
            out.append(rec)
        return out

    def verify_chain(self, experiment: str) -> bool:
        """Confirm the experiment's run chain is intact and untampered."""
        ph = self._ph()
        cur = self._conn.cursor()
        cur.execute(
            f"SELECT id, seq, ts, params_hash, returns, prev_hash, hash "
            f"FROM runs WHERE experiment = {ph} ORDER BY seq ASC",
            (experiment,),
        )
        prev = "genesis"
        for run_id, seq, ts, params_hash, returns_json, prev_hash, h in cur.fetchall():
            if prev_hash != prev:
                return False
            expected = _hash_payload(
                {
                    "id": run_id,
                    "experiment": experiment,
                    "seq": seq,
                    "ts": ts,
                    "params_hash": params_hash,
                    "returns_sha": hashlib.sha256(returns_json.encode()).hexdigest(),
                    "prev": prev,
                }
            )
            if h != expected:
                return False
            prev = h
        return True

    def close(self) -> None:
        try:
            self._conn.close()
        except Exception:
            pass
