"use client";

import { useState } from "react";
import { Crosshair, Upload, RefreshCw } from "lucide-react";
import type { AnalysisData, IntegrityReport } from "@/lib/types";
import { auditBacktest, type AuditPayload } from "@/lib/api";
import { RobustnessReport } from "@/components/ui/RobustnessReport";

type InputKind = "returns" | "equity" | "trades";

function parseNumbers(text: string): number[] {
    return text
        .split(/[\s,]+/)
        .map((t) => t.trim())
        .filter(Boolean)
        .map(Number)
        .filter((n) => Number.isFinite(n));
}

function parseMatrix(text: string): number[][] {
    const rows = text.trim().split(/\r?\n/).filter((r) => r.trim());
    return rows.map((r) => r.split(/[\s,]+/).map(Number).filter((n) => Number.isFinite(n)));
}

export function IntegrityTab({ data }: { data?: AnalysisData | null }) {
    const [kind, setKind] = useState<InputKind>("returns");
    const [raw, setRaw] = useState("");
    const [variantRaw, setVariantRaw] = useState("");
    const [turnover, setTurnover] = useState(1.0);
    const [nTrials, setNTrials] = useState(1);
    const [byoReport, setByoReport] = useState<IntegrityReport | null>(null);
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState<string | null>(null);

    const inputClass = "w-full px-3 py-2 rounded-lg bg-gray-50 dark:bg-[#0E1522] border border-gray-200 dark:border-[#28344B] text-sm focus:outline-none focus:ring-2 focus:ring-blue-500/50";
    const labelClass = "text-xs font-semibold uppercase tracking-wider text-gray-500 dark:text-gray-400 mb-1 block";

    const runAudit = async () => {
        const nums = parseNumbers(raw);
        if (nums.length < 2) { setError("Paste at least 2 numeric values."); return; }
        setLoading(true); setError(null);
        const payload: AuditPayload = { [kind]: nums, turnover, n_trials: nTrials } as AuditPayload;
        const vm = variantRaw.trim() ? parseMatrix(variantRaw) : null;
        if (vm && vm.length > 1) payload.variant_matrix = vm;
        try {
            setByoReport(await auditBacktest(payload));
        } catch (e) {
            setError(e instanceof Error ? e.message : "Audit failed");
        } finally {
            setLoading(false);
        }
    };

    return (
        <div role="tabpanel" id="panel-integrity" aria-labelledby="tab-integrity" className="space-y-8">
            {/* Audit of the strategy run in this dashboard */}
            {data?.integrity && (
                <section>
                    <h2 className="text-sm font-semibold uppercase tracking-wider text-gray-500 dark:text-gray-400 mb-4 flex items-center gap-2">
                        <Crosshair className="w-4 h-4" /> Overfitting Audit — This Strategy
                    </h2>
                    <RobustnessReport report={data.integrity} runId={data.run_id} />
                </section>
            )}

            {/* Bring-your-own-backtest auditor */}
            <section>
                <div className="bg-gradient-to-br from-blue-600/10 to-purple-600/10 rounded-xl p-5 border border-blue-500/20 mb-5">
                    <h2 className="text-base font-bold flex items-center gap-2 mb-1">
                        <Upload className="w-4 h-4 text-blue-500" /> Audit Your Own Backtest
                    </h2>
                    <p className="text-xs text-gray-500 dark:text-gray-400">
                        Built it in Backtrader, QuantConnect, Excel, or a notebook? Paste the result below to check whether the edge is real — no QuantProto engine required.
                    </p>
                </div>

                <div className="panel-card bg-white dark:bg-[#0B111C] rounded-2xl p-5 border border-gray-200 dark:border-[#1B2536] space-y-4">
                    <div className="flex flex-wrap gap-4">
                        <div className="w-40">
                            <label className={labelClass}>Input type</label>
                            <select value={kind} onChange={(e) => { setKind(e.target.value as InputKind); setError(null); }} className={inputClass}>
                                <option value="returns">Per-period returns</option>
                                <option value="equity">Equity / NAV curve</option>
                                <option value="trades">Trade returns</option>
                            </select>
                        </div>
                        <div className="w-32">
                            <label className={labelClass}>Turnover</label>
                            <input type="number" step="0.1" min={0} value={turnover} onChange={(e) => setTurnover(Number(e.target.value))} className={inputClass} />
                        </div>
                        <div className="w-32">
                            <label className={labelClass}># Trials tried</label>
                            <input type="number" min={1} value={nTrials} onChange={(e) => setNTrials(Math.max(1, Number(e.target.value)))} className={inputClass} />
                        </div>
                    </div>

                    <div>
                        <label className={labelClass}>{kind === "equity" ? "Equity values" : "Return values"} (comma/space/newline separated)</label>
                        <textarea value={raw} onChange={(e) => { setRaw(e.target.value); setError(null); }} rows={4} className={`${inputClass} font-mono`} placeholder="0.012, -0.004, 0.008, 0.001, ..." />
                    </div>

                    <details className="text-sm">
                        <summary className="cursor-pointer text-gray-500 hover:text-gray-300 select-none">Optional: paste all strategy variants (one per column) to compute PBO</summary>
                        <textarea value={variantRaw} onChange={(e) => setVariantRaw(e.target.value)} rows={4} className={`${inputClass} font-mono mt-2`} placeholder={"v1,v2,v3\n0.01,0.00,0.02\n-0.01,0.01,0.00\n..."} />
                    </details>

                    {error && <p className="text-sm text-red-400">{error}</p>}

                    <button onClick={runAudit} disabled={loading} className="h-10 px-6 rounded-lg bg-blue-600 hover:bg-blue-500 text-white font-semibold text-sm flex items-center gap-2 transition-colors disabled:opacity-50">
                        {loading ? <RefreshCw className="w-4 h-4 animate-spin" /> : <Crosshair className="w-4 h-4" />}
                        {loading ? "Auditing..." : "Audit Backtest"}
                    </button>
                </div>

                {byoReport && (
                    <div className="mt-6">
                        <RobustnessReport report={byoReport} />
                    </div>
                )}
            </section>
        </div>
    );
}
