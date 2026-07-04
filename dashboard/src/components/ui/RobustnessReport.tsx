import { ShieldCheck, ShieldAlert, ShieldX, AlertTriangle, CheckSquare, Info, ExternalLink } from "lucide-react";
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, ReferenceLine } from "recharts";
import type { IntegrityReport, RobustnessVerdict } from "@/lib/types";
import { ChartTooltip } from "@/components/ui/ChartTooltip";

const VERDICT_META: Record<RobustnessVerdict, { color: string; bg: string; border: string; icon: React.ElementType; label: string }> = {
    robust: { color: "text-emerald-400", bg: "bg-emerald-500/10", border: "border-emerald-500/30", icon: ShieldCheck, label: "Robust" },
    fragile: { color: "text-amber-400", bg: "bg-amber-500/10", border: "border-amber-500/30", icon: ShieldAlert, label: "Fragile" },
    likely_overfit: { color: "text-red-400", bg: "bg-red-500/10", border: "border-red-500/30", icon: ShieldX, label: "Likely Overfit" },
};

const SEVERITY_COLOR: Record<string, string> = {
    high: "text-red-400 bg-red-500/10 border-red-500/20",
    medium: "text-amber-400 bg-amber-500/10 border-amber-500/20",
    low: "text-blue-400 bg-blue-500/10 border-blue-500/20",
};

function Stat({ label, value, hint }: { label: string; value: string; hint?: string }) {
    return (
        <div className="bg-gray-50 dark:bg-[#15151A] rounded-lg p-3 border border-gray-200 dark:border-[#1F1F23]">
            <div className="text-[10px] font-semibold uppercase tracking-wider text-gray-500 dark:text-gray-400">{label}</div>
            <div className="text-base font-bold font-mono mt-0.5">{value}</div>
            {hint && <div className="text-[10px] text-gray-500 mt-0.5">{hint}</div>}
        </div>
    );
}

function ComponentBar({ label, value, max }: { label: string; value: number; max: number }) {
    const pct = max > 0 ? Math.max(0, Math.min(100, (value / max) * 100)) : 0;
    const color = pct >= 70 ? "bg-emerald-500" : pct >= 40 ? "bg-amber-500" : "bg-red-500";
    return (
        <div>
            <div className="flex justify-between text-xs mb-1">
                <span className="text-gray-600 dark:text-gray-300">{label}</span>
                <span className="font-mono text-gray-500">{value.toFixed(1)}/{max}</span>
            </div>
            <div className="h-2 rounded-full bg-gray-200 dark:bg-[#1F1F23] overflow-hidden">
                <div className={`h-full ${color} rounded-full transition-all`} style={{ width: `${pct}%` }} />
            </div>
        </div>
    );
}

export function RobustnessReport({ report, runId }: { report: IntegrityReport; runId?: string | null }) {
    const meta = VERDICT_META[report.verdict];
    const Icon = meta.icon;
    const s = report.statistics;
    const c = report.components;
    const shareId = runId ?? report.run_id;

    const costData = report.cost_curve.bps_grid.map((bps, i) => ({ bps, sharpe: report.cost_curve.net_sharpe[i] }));

    return (
        <div className="space-y-6">
            {/* Verdict banner + score */}
            <div className={`rounded-xl p-5 border ${meta.bg} ${meta.border} flex items-center gap-5`}>
                <div className="relative flex-shrink-0">
                    <div className={`w-24 h-24 rounded-full border-4 ${meta.border} flex flex-col items-center justify-center`}>
                        <span className={`text-3xl font-extrabold ${meta.color}`}>{report.score.toFixed(0)}</span>
                        <span className="text-[9px] uppercase tracking-wider text-gray-500">/ 100</span>
                    </div>
                </div>
                <div className="min-w-0">
                    <div className={`flex items-center gap-2 text-lg font-bold ${meta.color}`}>
                        <Icon className="w-5 h-5" /> {meta.label}
                    </div>
                    <p className="text-sm text-gray-600 dark:text-gray-300 mt-1">{report.headline}</p>
                    <p className="text-xs text-gray-500 mt-1">
                        Robustness Score blends statistical significance, selection-bias, cost survival, and sample adequacy — minus red-flag penalties.
                    </p>
                    {shareId && (
                        <a
                            href={`/api/runs/${shareId}/report`}
                            target="_blank"
                            rel="noopener noreferrer"
                            className="inline-flex items-center gap-1 text-xs text-blue-400 hover:text-blue-300 mt-2"
                        >
                            <ExternalLink className="w-3 h-3" /> Open shareable report
                        </a>
                    )}
                </div>
            </div>

            {/* Component breakdown + key statistics */}
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                <div className="bg-white dark:bg-[#0F0F12] rounded-xl p-5 border border-gray-200 dark:border-[#1F1F23]">
                    <h3 className="text-sm font-semibold uppercase tracking-wider text-gray-500 dark:text-gray-400 mb-4">Score Components</h3>
                    <div className="space-y-3">
                        <ComponentBar label="Significance (PSR / Deflated Sharpe)" value={c.significance} max={c.max.significance} />
                        <ComponentBar label="Selection robustness (PBO / DSR)" value={c.selection} max={c.max.selection} />
                        <ComponentBar label="Cost survival (break-even)" value={c.cost_survival} max={c.max.cost_survival} />
                        <ComponentBar label="Sample adequacy (track-record length)" value={c.sample_adequacy} max={c.max.sample_adequacy} />
                        {c.red_flag_penalty > 0 && (
                            <div className="text-xs text-red-400 pt-1">− {c.red_flag_penalty.toFixed(1)} red-flag penalty</div>
                        )}
                    </div>
                </div>

                <div className="bg-white dark:bg-[#0F0F12] rounded-xl p-5 border border-gray-200 dark:border-[#1F1F23]">
                    <h3 className="text-sm font-semibold uppercase tracking-wider text-gray-500 dark:text-gray-400 mb-4">Key Statistics</h3>
                    <div className="grid grid-cols-2 gap-3">
                        <Stat label="Annualised Sharpe" value={s.sharpe_annualized.toFixed(2)} />
                        <Stat label="Prob. Sharpe Ratio" value={`${(s.psr * 100).toFixed(1)}%`} hint="P(true Sharpe > 0)" />
                        <Stat label="Deflated Sharpe" value={s.dsr === null ? "—" : `${(s.dsr * 100).toFixed(1)}%`} hint={`${s.n_trials} trial(s)`} />
                        <Stat label="Break-even cost" value={s.breakeven_bps === null ? "∞" : `${s.breakeven_bps.toFixed(0)} bps`} hint="edge dies above this" />
                        <Stat label="Skew / Kurtosis" value={`${s.skew.toFixed(2)} / ${s.kurtosis.toFixed(1)}`} />
                        <Stat label="Min track record" value={s.min_track_record_length === null ? "∞" : `${s.min_track_record_length.toFixed(0)} obs`} hint={`have ${s.n_obs}`} />
                    </div>
                </div>
            </div>

            {/* PBO + cost-sensitivity curve */}
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                <div className="bg-white dark:bg-[#0F0F12] rounded-xl p-5 border border-gray-200 dark:border-[#1F1F23]">
                    <h3 className="text-sm font-semibold uppercase tracking-wider text-gray-500 dark:text-gray-400 mb-4">Probability of Backtest Overfitting</h3>
                    {report.pbo ? (
                        <div className="space-y-3">
                            <div className="flex items-end gap-2">
                                <span className={`text-4xl font-extrabold ${report.pbo.pbo > 0.5 ? "text-red-400" : report.pbo.pbo > 0.25 ? "text-amber-400" : "text-emerald-400"}`}>
                                    {(report.pbo.pbo * 100).toFixed(0)}%
                                </span>
                                <span className="text-xs text-gray-500 mb-1.5">probability the in-sample winner is overfit</span>
                            </div>
                            <div className="grid grid-cols-2 gap-3">
                                <Stat label="OOS degradation" value={report.pbo.oos_degradation.toFixed(3)} hint="IS − OOS Sharpe" />
                                <Stat label="P(OOS loss)" value={`${(report.pbo.prob_oos_loss * 100).toFixed(0)}%`} hint={`${report.pbo.n_configs} configs`} />
                            </div>
                        </div>
                    ) : (
                        <div className="flex items-start gap-2 text-sm text-gray-500">
                            <Info className="w-4 h-4 mt-0.5 flex-shrink-0" />
                            <span>PBO needs a matrix of strategy variants. Provide the returns of every configuration you tried (not just the best) to compute it.</span>
                        </div>
                    )}
                </div>

                <div className="bg-white dark:bg-[#0F0F12] rounded-xl p-5 border border-gray-200 dark:border-[#1F1F23]">
                    <h3 className="text-sm font-semibold uppercase tracking-wider text-gray-500 dark:text-gray-400 mb-4">Cost Sensitivity (net Sharpe vs bps)</h3>
                    <ResponsiveContainer width="100%" height={190}>
                        <LineChart data={costData}>
                            <CartesianGrid strokeDasharray="3 3" stroke="#1F1F23" />
                            <XAxis dataKey="bps" tick={{ fontSize: 10 }} stroke="#6B7280" unit="bps" />
                            <YAxis tick={{ fontSize: 10 }} stroke="#6B7280" />
                            <Tooltip content={<ChartTooltip />} />
                            <ReferenceLine y={0} stroke="#DC2626" strokeDasharray="4 4" />
                            <Line type="monotone" dataKey="sharpe" stroke="#2563EB" strokeWidth={2} dot={false} name="Net Sharpe" />
                        </LineChart>
                    </ResponsiveContainer>
                </div>
            </div>

            {/* Red flags */}
            {report.red_flags.length > 0 && (
                <div className="bg-white dark:bg-[#0F0F12] rounded-xl p-5 border border-gray-200 dark:border-[#1F1F23]">
                    <h3 className="text-sm font-semibold uppercase tracking-wider text-gray-500 dark:text-gray-400 mb-3 flex items-center gap-2">
                        <AlertTriangle className="w-4 h-4" /> Red Flags ({report.red_flags.length})
                    </h3>
                    <div className="space-y-2">
                        {report.red_flags.map((f, i) => (
                            <div key={i} className={`text-sm rounded-lg p-3 border ${SEVERITY_COLOR[f.severity] || SEVERITY_COLOR.low}`}>
                                <span className="font-semibold uppercase text-[10px] tracking-wider mr-2">{f.severity}</span>
                                {f.message}
                            </div>
                        ))}
                    </div>
                </div>
            )}

            {/* Manual integrity checklist */}
            <div className="bg-white dark:bg-[#0F0F12] rounded-xl p-5 border border-gray-200 dark:border-[#1F1F23]">
                <h3 className="text-sm font-semibold uppercase tracking-wider text-gray-500 dark:text-gray-400 mb-1 flex items-center gap-2">
                    <CheckSquare className="w-4 h-4" /> Manual Integrity Checklist
                </h3>
                <p className="text-xs text-gray-500 mb-3">These biases can&apos;t be proven from returns alone — confirm them against how the backtest was built.</p>
                <div className="space-y-2">
                    {report.checklist.map((item) => (
                        <div key={item.code} className="text-sm border border-gray-200 dark:border-[#1F1F23] rounded-lg p-3">
                            <div className="font-medium text-gray-700 dark:text-gray-200">{item.question}</div>
                            <div className="text-xs text-gray-500 mt-1">{item.why}</div>
                        </div>
                    ))}
                </div>
            </div>

            {report.notes.length > 0 && (
                <div className="text-xs text-gray-500 space-y-1">
                    {report.notes.map((n, i) => <p key={i} className="flex items-start gap-1.5"><Info className="w-3.5 h-3.5 mt-0.5 flex-shrink-0" />{n}</p>)}
                </div>
            )}
        </div>
    );
}
