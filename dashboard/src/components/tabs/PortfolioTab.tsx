import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Legend, Cell, PieChart as RPieChart, Pie } from "recharts";
import type { AnalysisData } from "@/lib/types";
import { ChartTooltip } from "@/components/ui/ChartTooltip";
import { PIE_COLORS } from "@/lib/api";

function buildPieData(weights: number[], tickers: string[]) {
    const significant: { name: string; value: number }[] = [];
    let otherTotal = 0;
    tickers.forEach((t, i) => {
        if (weights[i] >= 1.0) {
            significant.push({ name: t, value: weights[i] });
        } else {
            otherTotal += weights[i];
        }
    });
    if (otherTotal >= 0.1) {
        significant.push({ name: "Other", value: Math.round(otherTotal * 10) / 10 });
    }
    return significant;
}

export function PortfolioTab({ data }: { data: AnalysisData }) {
    return (
        <div role="tabpanel" id="panel-portfolio" aria-labelledby="tab-portfolio" className="space-y-6">
            <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
                {[
                    { name: "Mean-Variance", weights: data.portfolio.mean_variance },
                    { name: "Risk Parity", weights: data.portfolio.risk_parity },
                    { name: "Max Sharpe", weights: data.portfolio.max_sharpe },
                ].map(({ name, weights }) => {
                    const pieData = buildPieData(weights, data.portfolio.tickers);
                    return (
                        <div key={name} className="bg-white dark:bg-[#0F0F12] rounded-xl p-5 border border-gray-200 dark:border-[#1F1F23]">
                            <h3 className="text-sm font-semibold uppercase tracking-wider text-gray-500 dark:text-gray-400 mb-4">{name}</h3>
                            <ResponsiveContainer width="100%" height={200}>
                                <RPieChart>
                                    <Pie
                                        data={pieData}
                                        cx="50%" cy="50%" innerRadius={45} outerRadius={75}
                                        dataKey="value" nameKey="name"
                                        label={false} labelLine={false}
                                    >
                                        {pieData.map((_, i) => (
                                            <Cell key={i} fill={PIE_COLORS[i % PIE_COLORS.length]} />
                                        ))}
                                    </Pie>
                                    <Tooltip formatter={(v) => `${Number(v ?? 0).toFixed(1)}%`} />
                                </RPieChart>
                            </ResponsiveContainer>
                            {/* Legend */}
                            <div className="flex flex-wrap gap-x-3 gap-y-1 mt-2 justify-center">
                                {pieData.map((d, i) => (
                                    <div key={d.name} className="flex items-center gap-1 text-xs">
                                        <span className="w-2.5 h-2.5 rounded-sm flex-shrink-0" style={{ background: PIE_COLORS[i % PIE_COLORS.length] }} />
                                        <span className="text-gray-600 dark:text-gray-300">{d.name}: {d.value.toFixed(1)}%</span>
                                    </div>
                                ))}
                            </div>
                        </div>
                    );
                })}
            </div>

            <div className="bg-white dark:bg-[#0F0F12] rounded-xl p-5 border border-gray-200 dark:border-[#1F1F23]">
                <h3 className="text-sm font-semibold uppercase tracking-wider text-gray-500 dark:text-gray-400 mb-4">Allocation Comparison</h3>
                <ResponsiveContainer width="100%" height={320}>
                    <BarChart data={data.portfolio.tickers.map((t, i) => ({
                        ticker: t,
                        "Mean-Variance": data.portfolio.mean_variance[i],
                        "Risk Parity": data.portfolio.risk_parity[i],
                        "Max Sharpe": data.portfolio.max_sharpe[i],
                    }))} barGap={2} barCategoryGap="20%">
                        <CartesianGrid strokeDasharray="3 3" stroke="#1F1F23" />
                        <XAxis dataKey="ticker" tick={{ fontSize: 11 }} stroke="#6B7280" />
                        <YAxis tick={{ fontSize: 10 }} stroke="#6B7280" unit="%" />
                        <Tooltip content={<ChartTooltip />} />
                        <Legend wrapperStyle={{ fontSize: 12 }} />
                        <Bar dataKey="Mean-Variance" fill="#2563EB" radius={[4, 4, 0, 0]} />
                        <Bar dataKey="Risk Parity" fill="#059669" radius={[4, 4, 0, 0]} />
                        <Bar dataKey="Max Sharpe" fill="#9333EA" radius={[4, 4, 0, 0]} />
                    </BarChart>
                </ResponsiveContainer>
            </div>
        </div>
    );
}
