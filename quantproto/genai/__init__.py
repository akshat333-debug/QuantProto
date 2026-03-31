"""GenAI integration for QuantProto.

Uses Google Gemini for LLM-powered analysis. Falls back to mock
responses when GEMINI_API_KEY is not set.
"""

from __future__ import annotations

import os
import json
from typing import Any

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")


def _get_client():
    """Lazy-init Gemini client."""
    if not GEMINI_API_KEY:
        return None
    try:
        from google import genai
        return genai.Client(api_key=GEMINI_API_KEY)
    except Exception:
        return None


def is_available() -> bool:
    """Check if GenAI is available (API key set + SDK importable)."""
    return _get_client() is not None


def generate_summary(analysis_data: dict[str, Any]) -> str:
    """Generate an executive summary of the analysis results.

    Returns a Markdown-formatted summary.
    """
    client = _get_client()
    if client is None:
        return _mock_summary(analysis_data)

    prompt = _build_summary_prompt(analysis_data)
    try:
        response = client.models.generate_content(
            model="gemini-2.0-flash",
            contents=prompt,
        )
        return response.text or _mock_summary(analysis_data)
    except Exception as e:
        return f"*AI summary unavailable: {e}*\n\n" + _mock_summary(analysis_data)


def chat(question: str, analysis_data: dict[str, Any] | None = None) -> str:
    """Answer a user question about the analysis results.

    Returns a Markdown-formatted response.
    """
    client = _get_client()
    if client is None:
        return _mock_chat(question)

    prompt = _build_chat_prompt(question, analysis_data)
    try:
        response = client.models.generate_content(
            model="gemini-2.0-flash",
            contents=prompt,
        )
        return response.text or _mock_chat(question)
    except Exception as e:
        return f"*AI response unavailable: {e}*"


# ── Prompt builders ──────────────────────────────────────────────────

def _build_summary_prompt(data: dict[str, Any]) -> str:
    summary = data.get("summary", {})
    return f"""You are a quantitative research analyst. Generate a concise executive summary (3-5 paragraphs, Markdown formatted) for this portfolio analysis:

**Decision:** {summary.get('action', 'N/A')}
**Gate Passed:** {summary.get('gate_passed', 'N/A')}
**Total Return:** {summary.get('total_return', 'N/A')}%
**Sharpe Ratio:** {summary.get('sharpe', 'N/A')}
**Sortino Ratio:** {summary.get('sortino', 'N/A')}
**Max Drawdown:** {summary.get('max_drawdown', 'N/A')}%
**VaR (95%):** {summary.get('var_95', 'N/A')}%
**CVaR (95%):** {summary.get('cvar_95', 'N/A')}%
**Calmar Ratio:** {summary.get('calmar', 'N/A')}
**Pain Index:** {summary.get('pain_index', 'N/A')}%
**Bootstrap CI:** [{summary.get('bootstrap_ci', {}).get('lower', '?')}, {summary.get('bootstrap_ci', {}).get('upper', '?')}]
**Violations:** {json.dumps(summary.get('gate_violations', []))}
**Assets:** {json.dumps([a['ticker'] for a in data.get('assets', [])])}

Include: (1) overall assessment, (2) key risk concerns, (3) portfolio composition insight, (4) actionable recommendation. Use bullet points for clarity. Be specific with numbers."""


def _build_chat_prompt(question: str, data: dict[str, Any] | None) -> str:
    context = ""
    if data:
        summary = data.get("summary", {})
        context = f"""

Context — Latest analysis results:
- Decision: {summary.get('action')}, Gate: {'PASSED' if summary.get('gate_passed') else 'FAILED'}
- Return: {summary.get('total_return')}%, Sharpe: {summary.get('sharpe')}, Sortino: {summary.get('sortino')}
- Max DD: {summary.get('max_drawdown')}%, VaR: {summary.get('var_95')}%, CVaR: {summary.get('cvar_95')}%
- Assets: {json.dumps([a['ticker'] for a in data.get('assets', [])])}
- Violations: {json.dumps(summary.get('gate_violations', []))}"""

    return f"""You are a quantitative finance expert assistant for the QuantProto research engine. Answer the user's question concisely in Markdown.{context}

User question: {question}"""


# ── Mock responses ───────────────────────────────────────────────────

def _mock_summary(data: dict[str, Any]) -> str:
    s = data.get("summary", {})
    action = s.get("action", "N/A")
    ret = s.get("total_return", 0)
    sharpe = s.get("sharpe", 0)
    dd = s.get("max_drawdown", 0)
    violations = s.get("gate_violations", [])

    status = "✅ passed" if s.get("gate_passed") else "❌ failed"
    risk_note = f"There are **{len(violations)} risk gate violations** to address." if violations else "All risk gates were passed."

    return f"""## Executive Summary

The analysis pipeline returned a **{action}** decision. The risk gate {status}.

### Performance
- **Total Return:** {ret}% with a **Sharpe ratio of {sharpe}**
- **Maximum Drawdown:** {dd}%, indicating {'moderate' if abs(dd) < 15 else 'significant'} downside risk
- **Bootstrap Sharpe CI:** [{s.get('bootstrap_ci', {}).get('lower', '?')}, {s.get('bootstrap_ci', {}).get('upper', '?')}]

### Risk Assessment
{risk_note}

### Recommendation
{'The portfolio meets risk thresholds and can proceed to paper trading for further validation.' if s.get('gate_passed') else 'Address the risk gate violations before proceeding. Consider adjusting position sizing or factor weights.'}

*Configure `GEMINI_API_KEY` for AI-powered narrative analysis.*"""


def _mock_chat(question: str) -> str:
    return f"""I can help analyze your portfolio data, but **AI chat requires a Gemini API key**.

Set the `GEMINI_API_KEY` environment variable to enable AI-powered responses.

Your question: *"{question}"*

In the meantime, review the dashboard tabs for detailed metrics, charts, and risk analysis."""
