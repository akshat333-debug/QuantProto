import { AreaChart, Area, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from "recharts";
import type { AnalysisData } from "@/lib/types";
import { ChartTooltip } from "@/components/ui/ChartTooltip";

export function PerformanceTab({ data }: { data: AnalysisData }) {
    return (
        <div role="tabpanel" id="panel-equity" aria-labelledby="tab-equity" className="space-y-6">
            <div className="bg-white dark:bg-[#0F0F12] rounded-xl p-5 border border-gray-200 dark:border-[#1F1F23]">
                <h3 className="text-sm font-semibold uppercase tracking-wider text-gray-500 dark:text-gray-400 mb-4">Equity Curve</h3>
                <ResponsiveContainer width="100%" height={350}>
                    <AreaChart data={data.equity_curve.dates.map((d, i) => ({ date: d, equity: data.equity_curve.values[i] }))}>
                        <defs>
                            <linearGradient id="eqGrad2" x1="0" y1="0" x2="0" y2="1">
                                <stop offset="0%" stopColor="#059669" stopOpacity={0.3} />
                                <stop offset="100%" stopColor="#059669" stopOpacity={0} />
                            </linearGradient>
                        </defs>
                        <CartesianGrid strokeDasharray="3 3" stroke="#1F1F23" />
                        <XAxis dataKey="date" tick={{ fontSize: 10 }} stroke="#6B7280" tickFormatter={(v: string) => v.slice(5)} interval={Math.floor(data.equity_curve.dates.length / 8)} />
                        <YAxis tick={{ fontSize: 10 }} stroke="#6B7280" />
                        <Tooltip content={<ChartTooltip />} />
                        <Area type="monotone" dataKey="equity" stroke="#059669" fill="url(#eqGrad2)" strokeWidth={2} name="Equity" />
                    </AreaChart>
                </ResponsiveContainer>
            </div>

            <div className="bg-white dark:bg-[#0F0F12] rounded-xl p-5 border border-gray-200 dark:border-[#1F1F23]">
                <h3 className="text-sm font-semibold uppercase tracking-wider text-gray-500 dark:text-gray-400 mb-4">Drawdown</h3>
                <ResponsiveContainer width="100%" height={250}>
                    <AreaChart data={data.drawdown.dates.map((d, i) => ({ date: d, dd: data.drawdown.values[i] }))}>
                        <defs>
                            <linearGradient id="ddGrad" x1="0" y1="0" x2="0" y2="1">
                                <stop offset="0%" stopColor="#DC2626" stopOpacity={0.3} />
                                <stop offset="100%" stopColor="#DC2626" stopOpacity={0} />
                            </linearGradient>
                        </defs>
                        <CartesianGrid strokeDasharray="3 3" stroke="#1F1F23" />
                        <XAxis dataKey="date" tick={{ fontSize: 10 }} stroke="#6B7280" tickFormatter={(v: string) => v.slice(5)} interval={Math.floor(data.drawdown.dates.length / 8)} />
                        <YAxis tick={{ fontSize: 10 }} stroke="#6B7280" unit="%" />
                        <Tooltip content={<ChartTooltip />} />
                        <Area type="monotone" dataKey="dd" stroke="#DC2626" fill="url(#ddGrad)" strokeWidth={2} name="Drawdown %" />
                    </AreaChart>
                </ResponsiveContainer>
            </div>
        </div>
    );
}
