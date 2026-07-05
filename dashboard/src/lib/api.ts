/* ─── API Client ──────────────────────────────────────────────── */

import type { AnalysisData, StressData, IntegrityReport } from "./types";

/** Run the full analysis pipeline. */
export async function runAnalysis(opts: {
    tickers: string[];
    nDays: number;
    seed: number;
    dataSource: "synthetic" | "live";
    startDate: string;
    endDate: string;
    factorWeights?: Record<string, number>;
}): Promise<AnalysisData> {
    const res = await fetch("/api/run-analysis", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
            tickers: opts.tickers,
            n_days: opts.nDays,
            seed: opts.seed,
            data_source: opts.dataSource,
            start_date: opts.startDate,
            end_date: opts.endDate,
            factor_weights: opts.factorWeights ?? null,
        }),
    });
    if (!res.ok) {
        const errBody = await res.json().catch(() => ({ detail: res.statusText }));
        throw new Error(errBody.detail || `HTTP ${res.status}`);
    }
    return res.json();
}

/** Run a stress test scenario. */
export async function runStressTest(scenario: string, seed: number): Promise<StressData> {
    const res = await fetch("/api/stress-test", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ scenario, seed }),
    });
    if (!res.ok) {
        const errBody = await res.json().catch(() => ({ detail: res.statusText }));
        throw new Error(errBody.detail || `HTTP ${res.status}`);
    }
    return res.json();
}

/** Audit a bring-your-own backtest (returns / equity / trades). */
export type AuditPayload = {
    returns?: number[];
    equity?: number[];
    trades?: number[];
    capital?: number;
    variant_matrix?: number[][];
    n_trials?: number;
    turnover?: number;
};

export async function auditBacktest(payload: AuditPayload): Promise<IntegrityReport> {
    const res = await fetch("/api/audit", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
    });
    if (!res.ok) {
        const errBody = await res.json().catch(() => ({ detail: res.statusText }));
        throw new Error(errBody.detail || `HTTP ${res.status}`);
    }
    return res.json();
}

/** Fetch available stress test scenarios from backend. */
export async function fetchScenarios(): Promise<string[]> {
    const FALLBACK = ["2008_crisis", "covid_crash", "dotcom_bust", "flash_crash", "rate_hike"];
    try {
        const res = await fetch("/api/scenarios");
        const d: { scenarios: string[] } = await res.json();
        return d.scenarios?.length ? d.scenarios : FALLBACK;
    } catch {
        return FALLBACK;
    }
}

/** Pie chart colors. */
export const PIE_COLORS = ["#2563EB", "#059669", "#9333EA", "#DC2626", "#D97706", "#6366F1", "#EC4899"];

/* ─── AI API ─────────────────────────────────────────────────── */

/** Check if Gemini AI is available (API key set). */
export async function fetchAIStatus(): Promise<boolean> {
    try {
        const r = await fetch("/api/ai/status");
        const d: { available: boolean } = await r.json();
        return d.available;
    } catch { return false; }
}

/** Generate AI executive summary. */
export async function fetchAISummary(analysisData: Record<string, unknown>): Promise<{ summary: string; ai_powered: boolean }> {
    const res = await fetch("/api/ai/summary", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ analysis_data: analysisData }),
    });
    if (!res.ok) throw new Error("AI summary request failed");
    return res.json();
}

/** Send a chat message to the AI. */
export async function sendAIChat(question: string, analysisData?: Record<string, unknown>): Promise<{ response: string; ai_powered: boolean }> {
    const res = await fetch("/api/ai/chat", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ question, analysis_data: analysisData ?? null }),
    });
    if (!res.ok) throw new Error("AI chat request failed");
    return res.json();
}

/* ─── Experiment tracker API ─────────────────────────────────── */

import type { ExperimentSummary, ExperimentDetail, SensitivityResult } from "./types";

export async function fetchExperiments(): Promise<ExperimentSummary[]> {
    const res = await fetch("/api/experiments");
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    const d: { experiments: ExperimentSummary[] } = await res.json();
    return d.experiments;
}

export async function fetchExperimentDetail(name: string): Promise<ExperimentDetail> {
    const res = await fetch(`/api/experiments/${encodeURIComponent(name)}`);
    if (!res.ok) {
        const errBody = await res.json().catch(() => ({ detail: res.statusText }));
        throw new Error(errBody.detail || `HTTP ${res.status}`);
    }
    return res.json();
}

export async function fetchSensitivity(name: string, param: string): Promise<SensitivityResult> {
    const res = await fetch(`/api/experiments/${encodeURIComponent(name)}/sensitivity?param=${encodeURIComponent(param)}`);
    if (!res.ok) {
        const errBody = await res.json().catch(() => ({ detail: res.statusText }));
        throw new Error(errBody.detail || `HTTP ${res.status}`);
    }
    return res.json();
}
