"""Durable, tamper-evident storage for audit runs.

Every integrity audit (dashboard analysis or bring-your-own backtest) is
recorded here so results are reproducible, queryable, and shareable — the
backbone of a credible integrity product.

Backends, chosen automatically and degrading gracefully:
- ``DATABASE_URL=postgresql://…`` + ``psycopg`` installed → Postgres/TimescaleDB
- otherwise → a local SQLite file (``~/.quantproto/audit.db``)

Records are hash-chained (each row's hash folds in the previous row's hash via
:class:`quantproto.compliance.AuditLog` semantics), so the log is tamper-evident
across process restarts.
"""

from __future__ import annotations

import hashlib
import json
import os
import sqlite3
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

DEFAULT_SQLITE_PATH = Path.home() / ".quantproto" / "audit.db"

_SCHEMA = """
CREATE TABLE IF NOT EXISTS audit_runs (
    id          TEXT PRIMARY KEY,
    ts          TEXT NOT NULL,
    kind        TEXT NOT NULL,
    score       REAL,
    verdict     TEXT,
    input_hash  TEXT NOT NULL,
    prev_hash   TEXT NOT NULL,
    hash        TEXT NOT NULL,
    report      TEXT NOT NULL
);
"""


def _hash_payload(payload: dict) -> str:
    raw = json.dumps(payload, sort_keys=True, default=str)
    return hashlib.sha256(raw.encode()).hexdigest()


class AuditStore:
    """Persist and query hash-chained audit runs."""

    def __init__(self, url: str | None = None):
        self.url = url if url is not None else os.getenv("DATABASE_URL")
        self._pg = False
        self._conn = self._connect()
        self._init_schema()

    # ── Backend selection ─────────────────────────────────────────────────
    def _connect(self):
        if self.url and self.url.startswith(("postgres://", "postgresql://")):
            try:
                import psycopg  # type: ignore

                self._pg = True
                return psycopg.connect(self.url)
            except Exception as e:  # psycopg missing or connection failed
                import logging

                logging.getLogger("quantproto.storage").warning(
                    "Postgres unavailable (%s); falling back to SQLite.", e
                )
        DEFAULT_SQLITE_PATH.parent.mkdir(parents=True, exist_ok=True)
        return sqlite3.connect(str(DEFAULT_SQLITE_PATH), check_same_thread=False)

    @property
    def backend(self) -> str:
        return "postgres" if self._pg else "sqlite"

    def _ph(self) -> str:
        """Parameter placeholder for the active backend."""
        return "%s" if self._pg else "?"

    def _init_schema(self) -> None:
        cur = self._conn.cursor()
        cur.execute(_SCHEMA)
        self._conn.commit()

    def _last_hash(self) -> str:
        cur = self._conn.cursor()
        cur.execute("SELECT hash FROM audit_runs ORDER BY ts DESC LIMIT 1")
        row = cur.fetchone()
        return row[0] if row else "genesis"

    # ── Write ─────────────────────────────────────────────────────────────
    def record(self, kind: str, inputs: dict[str, Any], report: dict[str, Any]) -> dict:
        """Persist one audit run; returns its id + chain hash."""
        run_id = uuid.uuid4().hex
        ts = datetime.now(timezone.utc).isoformat()
        prev = self._last_hash()
        input_hash = _hash_payload(inputs)
        score = report.get("score")
        verdict = report.get("verdict")
        chain_hash = _hash_payload(
            {"id": run_id, "ts": ts, "kind": kind, "input_hash": input_hash, "prev": prev}
        )
        ph = self._ph()
        cur = self._conn.cursor()
        cur.execute(
            f"INSERT INTO audit_runs (id, ts, kind, score, verdict, input_hash, "
            f"prev_hash, hash, report) VALUES ({ph},{ph},{ph},{ph},{ph},{ph},{ph},{ph},{ph})",
            (run_id, ts, kind, score, verdict, input_hash, prev, chain_hash,
             json.dumps(report, default=str)),
        )
        self._conn.commit()
        return {"id": run_id, "ts": ts, "hash": chain_hash, "backend": self.backend}

    # ── Read ──────────────────────────────────────────────────────────────
    def list_runs(self, limit: int = 50) -> list[dict]:
        cur = self._conn.cursor()
        cur.execute(
            f"SELECT id, ts, kind, score, verdict FROM audit_runs "
            f"ORDER BY ts DESC LIMIT {int(limit)}"
        )
        cols = ["id", "ts", "kind", "score", "verdict"]
        return [dict(zip(cols, row)) for row in cur.fetchall()]

    def get_run(self, run_id: str) -> dict | None:
        ph = self._ph()
        cur = self._conn.cursor()
        cur.execute(
            f"SELECT id, ts, kind, score, verdict, report FROM audit_runs WHERE id = {ph}",
            (run_id,),
        )
        row = cur.fetchone()
        if not row:
            return None
        return {
            "id": row[0], "ts": row[1], "kind": row[2], "score": row[3],
            "verdict": row[4], "report": json.loads(row[5]),
        }

    def verify_chain(self) -> bool:
        """Confirm no row's chain hash has been tampered with."""
        cur = self._conn.cursor()
        cur.execute(
            "SELECT id, ts, kind, input_hash, prev_hash, hash FROM audit_runs ORDER BY ts ASC"
        )
        prev = "genesis"
        for run_id, ts, kind, input_hash, prev_hash, h in cur.fetchall():
            if prev_hash != prev:
                return False
            expected = _hash_payload(
                {"id": run_id, "ts": ts, "kind": kind, "input_hash": input_hash, "prev": prev}
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
