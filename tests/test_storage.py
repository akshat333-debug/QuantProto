"""Tests for the durable, hash-chained audit store (SQLite backend)."""

import sqlite3

import pytest

from quantproto.storage import AuditStore


@pytest.fixture
def store(tmp_path, monkeypatch):
    # Force the SQLite backend at a temp path, no DATABASE_URL.
    monkeypatch.delenv("DATABASE_URL", raising=False)
    db = tmp_path / "audit.db"
    import quantproto.storage as storage_mod
    monkeypatch.setattr(storage_mod, "DEFAULT_SQLITE_PATH", db)
    s = AuditStore()
    yield s
    s.close()


SAMPLE = {"score": 72.5, "verdict": "robust", "statistics": {"psr": 0.9}}


class TestAuditStore:
    def test_backend_is_sqlite(self, store):
        assert store.backend == "sqlite"

    def test_record_and_get(self, store):
        meta = store.record("byo", {"n_obs": 500}, SAMPLE)
        assert meta["id"]
        run = store.get_run(meta["id"])
        assert run["verdict"] == "robust"
        assert run["report"]["statistics"]["psr"] == 0.9

    def test_list_orders_recent_first(self, store):
        store.record("analysis", {"a": 1}, {"score": 10, "verdict": "likely_overfit"})
        store.record("byo", {"a": 2}, {"score": 90, "verdict": "robust"})
        runs = store.list_runs()
        assert len(runs) == 2
        assert runs[0]["score"] in (10, 90)

    def test_get_missing_returns_none(self, store):
        assert store.get_run("does-not-exist") is None

    def test_chain_verifies(self, store):
        for i in range(4):
            store.record("byo", {"i": i}, {"score": i, "verdict": "fragile"})
        assert store.verify_chain() is True

    def test_tamper_breaks_chain(self, store):
        store.record("byo", {"i": 0}, SAMPLE)
        store.record("byo", {"i": 1}, SAMPLE)
        # Corrupt a stored hash directly.
        cur = store._conn.cursor()
        cur.execute("UPDATE audit_runs SET hash = 'tampered' WHERE rowid = 1")
        store._conn.commit()
        assert store.verify_chain() is False
