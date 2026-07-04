"""Tests for the shareable HTML robustness report (permalink endpoint)."""

import numpy as np
import pytest
from fastapi.testclient import TestClient

from quantproto.dashboard.report_html import render_report_html
from quantproto.integrity.score import robustness_report


@pytest.fixture(scope="module")
def full_report():
    rng = np.random.default_rng(3)
    returns = rng.normal(0.0006, 0.01, 400)
    variants = rng.normal(0.0, 0.01, (400, 8))
    variants[:, 0] = returns
    return robustness_report(returns, n_trials=8, variant_matrix=variants)


def _run(report, **over):
    return {
        "id": "abc123def456", "ts": "2026-07-04T09:00:00+00:00",
        "kind": "byo", "score": report.get("score"),
        "verdict": report.get("verdict"), "report": report, **over,
    }


class TestRenderReportHtml:
    def test_contains_score_and_verdict(self, full_report):
        page = render_report_html(_run(full_report))
        assert "<!doctype html>" in page.lower()
        assert str(full_report["score"]) in page
        assert "abc123def456" in page

    def test_pbo_section_when_present(self, full_report):
        page = render_report_html(_run(full_report))
        assert "Probability of Backtest Overfitting" in page
        assert str(full_report["pbo"]["pbo"]) in page

    def test_pbo_placeholder_when_absent(self, full_report):
        report = {**full_report, "pbo": None}
        page = render_report_html(_run(report))
        assert "variant matrix" in page

    def test_cost_curve_svg(self, full_report):
        page = render_report_html(_run(full_report))
        assert "<svg" in page and "polyline" in page

    def test_escapes_untrusted_strings(self, full_report):
        report = {
            **full_report,
            "headline": "<script>alert(1)</script>",
            "red_flags": [{"severity": "high", "message": "<img src=x onerror=y>"}],
        }
        page = render_report_html(_run(report, id="<b>id</b>"))
        assert "<script>" not in page
        assert "<img src=x" not in page
        assert "<b>id</b>" not in page

    def test_survives_minimal_report(self):
        # Older or partial rows must still render, not crash.
        page = render_report_html(_run({"score": 50, "verdict": "fragile"}))
        assert "Fragile" in page


class TestReportEndpoint:
    @pytest.fixture
    def client(self, tmp_path, monkeypatch):
        monkeypatch.delenv("DATABASE_URL", raising=False)
        import quantproto.storage as storage_mod
        monkeypatch.setattr(storage_mod, "DEFAULT_SQLITE_PATH", tmp_path / "audit.db")
        import quantproto.dashboard.api as api_mod
        monkeypatch.setattr(api_mod, "_store", None)  # force re-init at temp path
        yield TestClient(api_mod.app)
        monkeypatch.setattr(api_mod, "_store", None)

    def test_permalink_roundtrip(self, client, full_report):
        import quantproto.dashboard.api as api_mod
        meta = api_mod._get_store().record("byo", {"n_obs": 400}, full_report)
        resp = client.get(f"/api/runs/{meta['id']}/report")
        assert resp.status_code == 200
        assert resp.headers["content-type"].startswith("text/html")
        assert str(full_report["score"]) in resp.text

    def test_unknown_run_404(self, client):
        assert client.get("/api/runs/doesnotexist/report").status_code == 404
