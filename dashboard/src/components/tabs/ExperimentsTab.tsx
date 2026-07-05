"use client";

import { useState, useEffect, useCallback } from "react";
import { FlaskConical, RefreshCw, ShieldCheck, ShieldAlert, Link2 } from "lucide-react";
import type { ExperimentSummary, ExperimentDetail, SensitivityResult } from "@/lib/types";
import { fetchExperiments, fetchExperimentDetail, fetchSensitivity } from "@/lib/api";

/* ─── Budget-state styling ────────────────────────────────────── */

const STATE_STYLE: Record<string, { badge: string; label: string }> = {
    ok: { badge: "bg-emerald-500/15 text-emerald-500 border-emerald-500/30", label: "OK" },
    warning: { badge: "bg-amber-500/15 text-amber-500 border-amber-500/30", label: "WARNING" },
    burned: { badge: "bg-red-500/15 text-red-500 border-red-500/30", label: "BURNED" },
    empty: { badge: "bg-gray-500/15 text-gray-500 border-gray-500/30", label: "EMPTY" },
};

const VERDICT_STYLE: Record<string, string> = {
    plateau: "text-emerald-500",
    soft_peak: "text-amber-500",
    sharp_peak: "text-red-500",
    inconclusive: "text-gray-500",
    insufficient: "text-gray-500",
};

const ANN = Math.sqrt(252);

function fmtParams(params: Record<string, unknown>): string {
    const s = Object.entries(params).map(([k, v]) => `${k}=${String(v)}`).join(", ");
    return s || "—";
}

function Stat({ label, value, hint }: { label: string; value: string; hint?: string }) {
    return (
        <div className="rounded-xl bg-gray-50 dark:bg-[#0E1522] border border-gray-200 dark:border-[#1B2536] px-4 py-3">
            <div className="text-[10px] font-semibold uppercase tracking-wider text-gray-500 dark:text-gray-400">{label}</div>
            <div className="text-lg font-bold tabular-nums">{value}</div>
            {hint && <div className="text-[10px] text-gray-500">{hint}</div>}
        </div>
    );
}

/* ─── Main tab ────────────────────────────────────────────────── */

export function ExperimentsTab() {
    const [experiments, setExperiments] = useState<ExperimentSummary[]>([]);
    const [selected, setSelected] = useState<string | null>(null);
    const [detail, setDetail] = useState<ExperimentDetail | null>(null);
    const [sensParam, setSensParam] = useState("");
    const [sens, setSens] = useState<SensitivityResult | null>(null);
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState<string | null>(null);

    const loadList = useCallback(async () => {
        try {
            const exps = await fetchExperiments();
            setExperiments(exps);
            if (exps.length > 0 && !selected) setSelected(exps[0].name);
        } catch (e) {
            setError(`Could not load experiments: ${e instanceof Error ? e.message : "unknown error"}. Is the API running on port 9000?`);
        }
    }, [selected]);

    const loadDetail = useCallback(async (name: string) => {
        setLoading(true); setError(null); setSens(null);
        try {
            setDetail(await fetchExperimentDetail(name));
        } catch (e) {
            setError(e instanceof Error ? e.message : "failed to load experiment");
            setDetail(null);
        } finally { setLoading(false); }
    }, []);

    useEffect(() => { loadList(); }, [loadList]);
    useEffect(() => { if (selected) loadDetail(selected); }, [selected, loadDetail]);

    const runSensitivity = useCallback(async () => {
        if (!selected || !sensParam.trim()) return;
        try { setSens(await fetchSensitivity(selected, sensParam.trim())); setError(null); }
        catch (e) { setError(e instanceof Error ? e.message : "sensitivity failed"); }
    }, [selected, sensParam]);

    const status = detail?.status;
    const state = STATE_STYLE[status?.budget_state ?? "empty"];
    const paramKeys = detail?.runs?.length
        ? Array.from(new Set(detail.runs.flatMap((r) => Object.keys(r.params))))
        : [];

    /* ── Empty state: onboarding snippet ── */
    if (experiments.length === 0) {
        return (
            <div className="rounded-2xl border border-gray-200 dark:border-[#1B2536] bg-white dark:bg-[#0B111C] p-8">
                {error && <p className="text-sm text-red-400 mb-4">{error}</p>}
                <div className="flex items-center gap-2 mb-3">
                    <FlaskConical className="w-5 h-5 text-blue-500" />
                    <h3 className="text-lg font-bold">No experiments tracked yet</h3>
                </div>
                <p className="text-sm text-gray-500 dark:text-gray-400 mb-4 max-w-xl">
                    Log every backtest configuration you try and QuantProto computes the honest
                    overfitting statistics from the observed search — no self-reported trial counts.
                </p>
                <pre className="rounded-xl bg-gray-50 dark:bg-[#0E1522] border border-gray-200 dark:border-[#1B2536] p-4 text-xs overflow-x-auto">
{`import quantproto as qp

exp = qp.experiment("my-strategy")
for lookback in range(5, 60, 5):
    returns = run_backtest(lookback=lookback)   # your engine
    exp.log(returns, params={"lookback": lookback})

exp.status()   # burned / warning / ok — before you trust the Sharpe`}
                </pre>
                <button onClick={loadList} className="mt-4 inline-flex items-center gap-2 text-xs font-semibold text-blue-500 hover:text-blue-400">
                    <RefreshCw className="w-3.5 h-3.5" /> Refresh
                </button>
            </div>
        );
    }

    return (
        <div className="space-y-6">
            {error && <p className="text-sm text-red-400">{error}</p>}

            {/* ── Selector row ── */}
            <div className="flex flex-wrap items-center gap-3">
                <select
                    value={selected ?? ""}
                    onChange={(e) => setSelected(e.target.value)}
                    className="h-9 px-3 rounded-lg bg-gray-50 dark:bg-[#0E1522] border border-gray-200 dark:border-[#1B2536] text-sm focus:outline-none focus:border-blue-500/60"
                >
                    {experiments.map((e) => (
                        <option key={e.name} value={e.name}>{e.name} ({e.n_runs} runs)</option>
                    ))}
                </select>
                <button onClick={() => { loadList(); if (selected) loadDetail(selected); }}
                    className="inline-flex items-center gap-1.5 h-9 px-3 rounded-lg border border-gray-200 dark:border-[#1B2536] text-xs font-semibold text-gray-600 dark:text-gray-300 hover:border-blue-500/60">
                    <RefreshCw className={`w-3.5 h-3.5 ${loading ? "animate-spin" : ""}`} /> Refresh
                </button>
                {detail && (
                    <span className={`inline-flex items-center gap-1.5 text-xs font-semibold ${detail.chain_valid ? "text-emerald-500" : "text-red-500"}`}>
                        {detail.chain_valid ? <ShieldCheck className="w-4 h-4" /> : <ShieldAlert className="w-4 h-4" />}
                        {detail.chain_valid ? "ledger chain intact" : "LEDGER TAMPERED"}
                    </span>
                )}
            </div>

            {/* ── Budget meter ── */}
            {status && status.budget_state !== "empty" && (
                <div className="rounded-2xl border border-gray-200 dark:border-[#1B2536] bg-white dark:bg-[#0B111C] p-5">
                    <div className="flex flex-wrap items-center justify-between gap-3 mb-4">
                        <div className="flex items-center gap-2">
                            <FlaskConical className="w-4 h-4 text-blue-500" />
                            <h3 className="text-xs font-bold uppercase tracking-widest text-gray-600 dark:text-gray-300">Research Budget</h3>
                        </div>
                        <span className={`px-3 py-1 rounded-full border text-xs font-bold ${state.badge}`}>{state.label}</span>
                    </div>
                    <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-3 mb-4">
                        <Stat label="Configs tried" value={`${status.n_configs}`} hint={`${status.n_runs} runs`} />
                        <Stat label="Best Sharpe" value={status.best_sharpe_ann?.toFixed(2) ?? "—"} hint="annualized" />
                        <Stat label="Noise benchmark" value={status.spurious_sharpe_ann?.toFixed(2) ?? "—"} hint="expected max from luck" />
                        <Stat label="Haircut Sharpe" value={status.haircut_sharpe_ann?.toFixed(2) ?? "—"} hint="what to expect OOS" />
                        <Stat label="DSR" value={status.dsr != null ? status.dsr.toFixed(3) : "—"} hint={`PSR ${status.psr?.toFixed(3) ?? "—"}`} />
                        <Stat label="PBO" value={status.pbo ? status.pbo.pbo.toFixed(3) : "—"} hint={status.pbo ? `P(OOS loss) ${status.pbo.prob_oos_loss.toFixed(2)}` : "needs ≥ 8 configs"} />
                    </div>
                    <p className="text-sm text-gray-600 dark:text-gray-300">{status.message}</p>
                    {status.best_params && (
                        <p className="text-xs text-gray-500 mt-2">Best config: <span className="font-mono">{fmtParams(status.best_params)}</span></p>
                    )}
                </div>
            )}

            {/* ── Parameter sensitivity ── */}
            {paramKeys.length > 0 && (
                <div className="rounded-2xl border border-gray-200 dark:border-[#1B2536] bg-white dark:bg-[#0B111C] p-5">
                    <h3 className="text-xs font-bold uppercase tracking-widest text-gray-600 dark:text-gray-300 mb-3">Parameter Sensitivity</h3>
                    <div className="flex flex-wrap items-center gap-2 mb-4">
                        {paramKeys.map((k) => (
                            <button key={k} onClick={() => { setSensParam(k); }}
                                className={`px-3 py-1.5 rounded-lg border text-xs font-semibold transition-colors ${sensParam === k
                                    ? "border-blue-500/60 text-blue-500 bg-blue-500/10"
                                    : "border-gray-200 dark:border-[#1B2536] text-gray-600 dark:text-gray-300 hover:border-blue-500/40"}`}>
                                {k}
                            </button>
                        ))}
                        <button onClick={runSensitivity} disabled={!sensParam}
                            className="h-8 px-4 rounded-lg bg-blue-600 hover:bg-blue-500 text-white text-xs font-semibold disabled:opacity-50">
                            Analyze
                        </button>
                    </div>
                    {sens && (
                        <div>
                            {sens.sharpe_ann_by_value && (
                                <div className="space-y-1.5 mb-3">
                                    {sens.values.map((v, i) => {
                                        const s = sens.sharpe_ann_by_value![i];
                                        const maxAbs = Math.max(...sens.sharpe_ann_by_value!.map(Math.abs), 0.001);
                                        const width = Math.abs(s) / maxAbs * 100;
                                        const isPeak = v === sens.peak_value;
                                        return (
                                            <div key={String(v)} className="flex items-center gap-2 text-xs">
                                                <span className="w-20 font-mono text-gray-500 flex-shrink-0">{sens.param}={String(v)}</span>
                                                <div className="flex-1 h-4 rounded bg-gray-100 dark:bg-[#0E1522] overflow-hidden">
                                                    <div className={`h-full rounded ${s >= 0 ? (isPeak ? "bg-blue-500" : "bg-blue-500/40") : "bg-red-500/50"}`}
                                                        style={{ width: `${width}%` }} />
                                                </div>
                                                <span className={`w-14 text-right tabular-nums ${isPeak ? "font-bold" : ""}`}>{s.toFixed(2)}</span>
                                            </div>
                                        );
                                    })}
                                </div>
                            )}
                            <p className={`text-sm font-semibold ${VERDICT_STYLE[sens.verdict]}`}>{sens.verdict.replace("_", " ")}</p>
                            <p className="text-xs text-gray-500 dark:text-gray-400">{sens.message}</p>
                        </div>
                    )}
                </div>
            )}

            {/* ── Runs table ── */}
            {detail && detail.runs.length > 0 && (
                <div className="rounded-2xl border border-gray-200 dark:border-[#1B2536] bg-white dark:bg-[#0B111C] p-5 overflow-x-auto">
                    <h3 className="text-xs font-bold uppercase tracking-widest text-gray-600 dark:text-gray-300 mb-3">
                        Run History <span className="text-gray-400 font-normal">({detail.runs.length})</span>
                    </h3>
                    <table className="w-full text-xs">
                        <thead>
                            <tr className="text-left text-gray-500 border-b border-gray-200 dark:border-[#1B2536]">
                                <th className="py-2 pr-3 font-semibold">#</th>
                                <th className="py-2 pr-3 font-semibold">Time</th>
                                <th className="py-2 pr-3 font-semibold">Source</th>
                                <th className="py-2 pr-3 font-semibold">Obs</th>
                                <th className="py-2 pr-3 font-semibold">Sharpe (ann)</th>
                                <th className="py-2 pr-3 font-semibold">Params</th>
                                <th className="py-2 font-semibold"><Link2 className="w-3 h-3 inline" /></th>
                            </tr>
                        </thead>
                        <tbody>
                            {[...detail.runs].reverse().map((r) => (
                                <tr key={r.id} className="border-b border-gray-100 dark:border-[#131B2A] last:border-0">
                                    <td className="py-1.5 pr-3 text-gray-500">{r.seq}</td>
                                    <td className="py-1.5 pr-3 text-gray-500 whitespace-nowrap">{r.ts.slice(0, 19).replace("T", " ")}</td>
                                    <td className="py-1.5 pr-3">{r.source}</td>
                                    <td className="py-1.5 pr-3 tabular-nums">{r.n_obs}</td>
                                    <td className={`py-1.5 pr-3 tabular-nums font-semibold ${r.sharpe * ANN >= 0 ? "text-emerald-500" : "text-red-400"}`}>
                                        {(r.sharpe * ANN).toFixed(2)}
                                    </td>
                                    <td className="py-1.5 pr-3 font-mono text-gray-600 dark:text-gray-300">{fmtParams(r.params)}</td>
                                    <td className="py-1.5 text-gray-400" title={r.code_hash ? `code ${r.code_hash.slice(0, 12)}` : "no code hash"}>
                                        {r.code_hash ? "✓" : "—"}
                                    </td>
                                </tr>
                            ))}
                        </tbody>
                    </table>
                </div>
            )}
        </div>
    );
}
