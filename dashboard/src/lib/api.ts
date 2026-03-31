/* ─── API Client ──────────────────────────────────────────────── */

import type { AnalysisData, StressData } from "./types";

/** Run the full analysis pipeline. */
export async function runAnalysis(opts: {
    tickers: string[];
    nDays: number;
    seed: number;
    dataSource: "synthetic" | "live";
    startDate: string;
    endDate: string;
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
