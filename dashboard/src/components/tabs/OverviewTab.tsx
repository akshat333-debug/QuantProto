import { Activity, TrendingUp, TrendingDown, Shield, AlertTriangle, Target, Layers } from "lucide-react";
import { AreaChart, Area, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from "recharts";
import type { AnalysisData } from "@/lib/types";
import { MetricCard } from "@/components/ui/MetricCard";
import { DecisionBadge } from "@/components/ui/DecisionBadge";
import { ChartTooltip } from "@/components/ui/ChartTooltip";

export function OverviewTab({ data }: { data: AnalysisData }) {
    return (
        <div role="tabpanel" id="panel-overview" aria-labelledby="tab-overview" className="space-y-6">
            <div className="flex items-center gap-4 mb-2">
                <DecisionBadge action={data.summary.action} passed={data.summary.gate_passed} />
                <span className="text-sm text-gray-500 dark:text-gray-400">
                    Sharpe 95% CI: [{data.summary.bootstrap_ci.lower}, {data.summary.bootstrap_ci.upper}]
                </span>
            </div>

            <div className="grid grid-cols-2 lg:grid-cols-4 gap-3 sm:gap-4">
                <MetricCard label="Total Return" value={`${data.summary.total_return > 0 ? "+" : ""}${data.summary.total_return}%`} icon={TrendingUp} color={data.summary.total_return >= 0 ? "text-emerald-500" : "text-red-500"} />
                <MetricCard label="Sharpe Ratio" value={data.summary.sharpe.toFixed(2)} sub="Annualised" icon={Target} color={data.summary.sharpe >= 1 ? "text-emerald-500" : data.summary.sharpe >= 0.5 ? "text-amber-500" : "text-red-500"} />
                <MetricCard label="Max Drawdown" value={`${data.summary.max_drawdown}%`} sub="Peak to trough" icon={TrendingDown} color="text-red-500" />
                <MetricCard label="VaR (95%)" value={`${data.summary.var_95}%`} sub="Daily" icon={Shield} color="text-amber-500" />
            </div>

            <div className="grid grid-cols-2 lg:grid-cols-4 gap-3 sm:gap-4">
                <MetricCard label="Sortino" value={data.summary.sortino.toFixed(2)} icon={Activity} color="text-blue-500" />
                <MetricCard label="CVaR (95%)" value={`${data.summary.cvar_95}%`} icon={AlertTriangle} color="text-red-500" />
                <MetricCard label="Calmar" value={data.summary.calmar.toFixed(2)} icon={Layers} color="text-purple-500" />
                <MetricCard label="Pain Index" value={`${data.summary.pain_index}%`} icon={Activity} color="text-amber-500" />
            </div>

            {/* Mini equity curve */}
            <div className="bg-white dark:bg-[#0F0F12] rounded-xl p-5 border border-gray-200 dark:border-[#1F1F23]">
                <h3 className="text-sm font-semibold uppercase tracking-wider text-gray-500 dark:text-gray-400 mb-4">Equity Curve</h3>
                <ResponsiveContainer width="100%" height={300}>
                    <AreaChart data={data.equity_curve.dates.map((d, i) => ({ date: d, equity: data.equity_curve.values[i] }))}>
                        <defs>
                            <linearGradient id="eqGrad" x1="0" y1="0" x2="0" y2="1">
                                <stop offset="0%" stopColor="#2563EB" stopOpacity={0.3} />
                                <stop offset="100%" stopColor="#2563EB" stopOpacity={0} />
                            </linearGradient>
                        </defs>
                        <CartesianGrid strokeDasharray="3 3" stroke="#1F1F23" />
                        <XAxis dataKey="date" tick={{ fontSize: 10 }} stroke="#6B7280" tickFormatter={(v: string) => v.slice(5)} interval={Math.floor(data.equity_curve.dates.length / 8)} />
                        <YAxis tick={{ fontSize: 10 }} stroke="#6B7280" />
                        <Tooltip content={<ChartTooltip />} />
                        <Area type="monotone" dataKey="equity" stroke="#2563EB" fill="url(#eqGrad)" strokeWidth={2} name="Equity" />
                    </AreaChart>
                </ResponsiveContainer>
            </div>

            {/* Asset breakdown table */}
            <div className="bg-white dark:bg-[#0F0F12] rounded-xl p-5 border border-gray-200 dark:border-[#1F1F23]">
                <h3 className="text-sm font-semibold uppercase tracking-wider text-gray-500 dark:text-gray-400 mb-4">Asset Breakdown</h3>
                <div className="overflow-x-auto">
                    <table className="w-full text-sm">
                        <thead>
                            <tr className="border-b border-gray-200 dark:border-[#1F1F23]">
                                <th className="text-left py-2 px-3 text-xs font-semibold uppercase text-gray-500 dark:text-gray-400">Ticker</th>
                                <th className="text-right py-2 px-3 text-xs font-semibold uppercase text-gray-500 dark:text-gray-400">Price</th>
                                <th className="text-right py-2 px-3 text-xs font-semibold uppercase text-gray-500 dark:text-gray-400">Ann. Return</th>
                                <th className="text-right py-2 px-3 text-xs font-semibold uppercase text-gray-500 dark:text-gray-400">Ann. Vol</th>
                                <th className="text-right py-2 px-3 text-xs font-semibold uppercase text-gray-500 dark:text-gray-400">Sharpe</th>
                                <th className="text-right py-2 px-3 text-xs font-semibold uppercase text-gray-500 dark:text-gray-400">Max DD</th>
                            </tr>
                        </thead>
                        <tbody>
                            {data.assets.map((a) => (
                                <tr key={a.ticker} className="border-b border-gray-100 dark:border-[#1A1A1E]">
                                    <td className="py-2 px-3 font-medium">{a.ticker}</td>
                                    <td className="py-2 px-3 text-right">${a.latest_price.toFixed(2)}</td>
                                    <td className={`py-2 px-3 text-right font-medium ${a.annualised_return >= 0 ? "text-emerald-500" : "text-red-500"}`}>
                                        {a.annualised_return > 0 ? "+" : ""}{a.annualised_return.toFixed(1)}%
                                    </td>
                                    <td className="py-2 px-3 text-right">{a.annualised_vol.toFixed(1)}%</td>
                                    <td className={`py-2 px-3 text-right ${a.sharpe >= 1 ? "text-emerald-500" : a.sharpe >= 0 ? "text-amber-500" : "text-red-500"}`}>
                                        {a.sharpe.toFixed(2)}
                                    </td>
                                    <td className="py-2 px-3 text-right text-red-500">{a.max_drawdown.toFixed(1)}%</td>
                                </tr>
                            ))}
                        </tbody>
                    </table>
                </div>
            </div>
        </div>
    );
}
