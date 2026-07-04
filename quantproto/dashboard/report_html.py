"""Standalone HTML rendering for persisted audit runs.

Turns a stored run (see :class:`quantproto.storage.AuditStore`) into a single
self-contained HTML page — no JS frameworks, no external assets — so a
robustness report can be shared as a permalink with a PM, allocator, or
teammate who never opens the dashboard.
"""

from __future__ import annotations

import html
from typing import Any

_VERDICT_STYLE = {
    "robust": ("#22c55e", "Robust", "Edge is plausibly real."),
    "fragile": ("#f59e0b", "Fragile", "Some evidence of edge, but weaknesses found."),
    "likely_overfit": ("#ef4444", "Likely Overfit",
                       "Treat this backtest as noise until proven otherwise."),
}

_SEVERITY_COLOR = {"high": "#ef4444", "medium": "#f59e0b", "low": "#94a3b8"}

_CSS = """
:root { color-scheme: dark; }
* { box-sizing: border-box; margin: 0; }
body { background:
    radial-gradient(1200px 500px at 15% -10%, rgba(59, 130, 246, 0.07), transparent 60%),
    radial-gradient(1000px 450px at 85% -15%, rgba(139, 92, 246, 0.06), transparent 60%),
    #05070c;
  color: #e8ecf4; font: 15px/1.55 -apple-system,
       BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; padding: 32px 16px; }
.wrap { max-width: 760px; margin: 0 auto; }
h1 { font-size: 20px; letter-spacing: .02em; }
h2 { font-size: 13px; text-transform: uppercase; letter-spacing: .08em;
     color: #94a3b8; margin: 28px 0 10px; }
.meta { color: #64748b; font-size: 12px; margin-top: 4px; word-break: break-all; }
.card { background: #0b111c; border: 1px solid #1b2536; border-radius: 16px;
        padding: 20px; margin-top: 16px; }
.scorebox { display: flex; align-items: center; gap: 24px; }
.score { font-size: 52px; font-weight: 700; line-height: 1; }
.score small { font-size: 16px; color: #64748b; font-weight: 400; }
.badge { display: inline-block; padding: 4px 12px; border-radius: 999px;
         font-weight: 600; font-size: 14px; }
.headline { color: #94a3b8; margin-top: 6px; }
table { width: 100%; border-collapse: collapse; font-size: 14px; }
td, th { padding: 7px 8px; border-bottom: 1px solid #1b2536; text-align: left; }
td:last-child { text-align: right; font-variant-numeric: tabular-nums; }
.bar { background: #1b2536; border-radius: 4px; height: 8px; overflow: hidden; }
.bar > div { height: 100%; border-radius: 4px; background: #22c55e; }
.flag { display: flex; gap: 10px; padding: 8px 0; border-bottom: 1px solid #1b2536;
        font-size: 14px; }
.dot { flex: none; width: 8px; height: 8px; border-radius: 50%; margin-top: 7px; }
.footer { color: #475569; font-size: 12px; margin-top: 28px; }
svg text { fill: #64748b; font-size: 10px; }
"""


def _esc(v: Any) -> str:
    return html.escape(str(v))


def _fmt(v: Any) -> str:
    if v is None:
        return "—"
    if isinstance(v, float):
        return f"{v:,.4g}"
    return _esc(v)


def _component_rows(components: dict) -> str:
    maxes = components.get("max", {})
    labels = {
        "significance": "Significance (PSR / Deflated Sharpe)",
        "selection": "Selection robustness (PBO / DSR)",
        "cost_survival": "Cost survival (break-even)",
        "sample_adequacy": "Sample adequacy (track record)",
    }
    rows = []
    for key, label in labels.items():
        got = components.get(key)
        cap = maxes.get(key)
        if got is None or not cap:
            continue
        pct = max(0.0, min(100.0, 100.0 * float(got) / float(cap)))
        rows.append(
            f"<tr><td>{label}</td>"
            f"<td style='width:40%'><div class='bar'><div style='width:{pct:.0f}%'>"
            f"</div></div></td><td>{_fmt(got)}/{_fmt(cap)}</td></tr>"
        )
    penalty = components.get("red_flag_penalty")
    if penalty:
        rows.append(
            f"<tr><td>Red-flag penalty</td><td></td>"
            f"<td style='color:#ef4444'>−{_fmt(penalty)}</td></tr>"
        )
    return "".join(rows)


def _stat_rows(stats: dict) -> str:
    labels = [
        ("sharpe_annualized", "Annualised Sharpe"),
        ("psr", "Probabilistic Sharpe Ratio"),
        ("dsr", "Deflated Sharpe Ratio"),
        ("n_trials", "Configurations tried"),
        ("n_obs", "Observations"),
        ("skew", "Skew"),
        ("kurtosis", "Kurtosis"),
        ("min_track_record_length", "Minimum track record (obs)"),
        ("breakeven_bps", "Cost break-even (bps)"),
    ]
    return "".join(
        f"<tr><td>{label}</td><td>{_fmt(stats.get(key))}</td></tr>"
        for key, label in labels
        if key in stats
    )


def _pbo_section(pbo: dict | None) -> str:
    if not pbo:
        return ("<h2>Probability of Backtest Overfitting</h2><div class='card'>"
                "<p class='meta'>Not computed — a variant matrix (returns of every "
                "configuration tried) was not provided for this run.</p></div>")
    rows = "".join(
        f"<tr><td>{label}</td><td>{_fmt(pbo.get(key))}</td></tr>"
        for key, label in [
            ("pbo", "PBO (0 = generalises, 1 = pure overfit)"),
            ("oos_degradation", "In-sample → out-of-sample degradation"),
            ("prob_oos_loss", "Probability of OOS loss"),
            ("n_configs", "Configurations in matrix"),
        ]
    )
    return f"<h2>Probability of Backtest Overfitting</h2><div class='card'><table>{rows}</table></div>"


def _cost_curve_svg(curve: dict | None) -> str:
    grid = (curve or {}).get("bps_grid") or []
    sharpe = (curve or {}).get("net_sharpe") or []
    if len(grid) < 2 or len(grid) != len(sharpe):
        return ""
    w, h, pad = 680, 160, 28
    lo = min(min(sharpe), 0.0)
    hi = max(max(sharpe), 0.0)
    span = (hi - lo) or 1.0
    xs = [pad + (w - 2 * pad) * i / (len(grid) - 1) for i in range(len(grid))]
    ys = [h - pad - (h - 2 * pad) * (s - lo) / span for s in sharpe]
    pts = " ".join(f"{x:.1f},{y:.1f}" for x, y in zip(xs, ys))
    zero_y = h - pad - (h - 2 * pad) * (0.0 - lo) / span
    ticks = "".join(
        f"<text x='{x:.0f}' y='{h - 8}' text-anchor='middle'>{g:g}</text>"
        for x, g in list(zip(xs, grid))[:: max(1, len(grid) // 8)]
    )
    return (
        "<h2>Net Sharpe vs transaction cost (bps)</h2><div class='card'>"
        f"<svg viewBox='0 0 {w} {h}' width='100%' role='img' "
        "aria-label='Net Sharpe across transaction-cost levels'>"
        f"<line x1='{pad}' y1='{zero_y:.1f}' x2='{w - pad}' y2='{zero_y:.1f}' "
        "stroke='#334155' stroke-dasharray='4 4'/>"
        f"<polyline points='{pts}' fill='none' stroke='#38bdf8' stroke-width='2'/>"
        f"{ticks}</svg></div>"
    )


def _flags_section(flags: list) -> str:
    if not flags:
        return ("<h2>Red flags</h2><div class='card'>"
                "<p class='meta'>No statistical red flags detected.</p></div>")
    items = "".join(
        f"<div class='flag'><span class='dot' style='background:"
        f"{_SEVERITY_COLOR.get(str(f.get('severity', 'low')).lower(), '#94a3b8')}'></span>"
        f"<span><strong>{_esc(str(f.get('severity', '')).upper())}</strong> — "
        f"{_esc(f.get('message', ''))}</span></div>"
        for f in flags
    )
    return f"<h2>Red flags</h2><div class='card'>{items}</div>"


def _checklist_section(checklist: list) -> str:
    if not checklist:
        return ""
    items = "".join(
        f"<div class='flag'><span class='dot' style='background:#64748b'></span>"
        f"<span>{_esc(item.get('item', item) if isinstance(item, dict) else item)}"
        + (f"<br><span class='meta'>{_esc(item['why'])}</span>"
           if isinstance(item, dict) and item.get("why") else "")
        + "</span></div>"
        for item in checklist
    )
    return ("<h2>Manual checklist — cannot be detected from returns alone</h2>"
            f"<div class='card'>{items}</div>")


def render_report_html(run: dict) -> str:
    """Render one persisted audit run as a self-contained HTML page."""
    report = run.get("report") or {}
    verdict = str(report.get("verdict", "fragile"))
    color, verdict_label, verdict_blurb = _VERDICT_STYLE.get(
        verdict, ("#94a3b8", verdict or "Unknown", "")
    )
    score = report.get("score")
    headline = report.get("headline") or verdict_blurb

    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>QuantProto Robustness Report — {_esc(run.get('id', ''))[:12]}</title>
<style>{_CSS}</style>
</head>
<body><div class="wrap">
<h1>QuantProto — Robustness Report</h1>
<p class="meta">Run {_esc(run.get('id', ''))} · {_esc(run.get('kind', ''))} ·
{_esc(run.get('ts', ''))}</p>

<div class="card scorebox">
  <div class="score" style="color:{color}">{_fmt(score)}<small> /100</small></div>
  <div>
    <span class="badge" style="background:{color}22;color:{color}">{verdict_label}</span>
    <p class="headline">{_esc(headline)}</p>
  </div>
</div>

<h2>Score components</h2>
<div class="card"><table>{_component_rows(report.get('components') or {})}</table></div>

<h2>Key statistics</h2>
<div class="card"><table>{_stat_rows(report.get('statistics') or {})}</table></div>

{_pbo_section(report.get('pbo'))}
{_cost_curve_svg(report.get('cost_curve'))}
{_flags_section(report.get('red_flags') or [])}
{_checklist_section(report.get('checklist') or [])}

<p class="footer">Generated by QuantProto — backtest-integrity auditor.
This run is stored in a hash-chained, tamper-evident audit log.</p>
</div></body></html>"""
