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
