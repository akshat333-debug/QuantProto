import { AlertTriangle } from "lucide-react";
import { LineChart, Line, BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from "recharts";
import type { AnalysisData } from "@/lib/types";
import { ChartTooltip } from "@/components/ui/ChartTooltip";

export function RiskTab({ data }: { data: AnalysisData }) {
    return (
        <div role="tabpanel" id="panel-risk" aria-labelledby="tab-risk" className="space-y-6">
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                <div className="bg-white dark:bg-[#0F0F12] rounded-xl p-5 border border-gray-200 dark:border-[#1F1F23]">
                    <h3 className="text-sm font-semibold uppercase tracking-wider text-gray-500 dark:text-gray-400 mb-4">Correlation Matrix</h3>
                    <div className="overflow-x-auto">
                        <table className="text-xs border-separate" style={{ borderSpacing: "4px" }}>
                            <thead>
                                <tr>
                                    <th className="pb-2 w-14"></th>
                                    {data.correlation.tickers.map((t) => (
                                        <th key={t} className="pb-2 px-3 font-semibold text-center min-w-[54px]">{t}</th>
                                    ))}
                                </tr>
                            </thead>
                            <tbody>
                                {data.correlation.tickers.map((t, i) => (
                                    <tr key={t}>
                                        <td className="py-2 pr-2 font-semibold text-right">{t}</td>
                                        {data.correlation.matrix[i].map((v, j) => (
                                            <td key={j} className="py-2 px-3 text-center font-mono" style={{
                                                backgroundColor: `rgba(${v > 0 ? "5,150,105" : "220,38,38"}, ${Math.abs(v) * 0.5})`,
                                                borderRadius: "6px",
                                                minWidth: "54px",
                                            }}>
                                                {v.toFixed(2)}
                                            </td>
                                        ))}
                                    </tr>
                                ))}
                            </tbody>
                        </table>
                    </div>
                </div>

                <div className="bg-white dark:bg-[#0F0F12] rounded-xl p-5 border border-gray-200 dark:border-[#1F1F23]">
                    <h3 className="text-sm font-semibold uppercase tracking-wider text-gray-500 dark:text-gray-400 mb-4">Rolling Mean Correlation</h3>
                    <ResponsiveContainer width="100%" height={250}>
                        <LineChart data={data.rolling_correlation.dates.map((d, i) => ({ date: d, corr: data.rolling_correlation.values[i] }))}>
                            <CartesianGrid strokeDasharray="3 3" stroke="#1F1F23" />
                            <XAxis dataKey="date" tick={{ fontSize: 10 }} stroke="#6B7280" tickFormatter={(v: string) => v.slice(5)} interval={Math.floor(data.rolling_correlation.dates.length / 6)} />
                            <YAxis tick={{ fontSize: 10 }} stroke="#6B7280" />
                            <Tooltip content={<ChartTooltip />} />
                            <Line type="monotone" dataKey="corr" stroke="#9333EA" strokeWidth={2} dot={false} name="Mean Correlation" />
                        </LineChart>
                    </ResponsiveContainer>
                </div>
            </div>

            <div className="bg-white dark:bg-[#0F0F12] rounded-xl p-5 border border-gray-200 dark:border-[#1F1F23]">
                <h3 className="text-sm font-semibold uppercase tracking-wider text-gray-500 dark:text-gray-400 mb-4">PCA Explained Variance</h3>
                <ResponsiveContainer width="100%" height={200}>
                    <BarChart data={data.pca.components.map((c, i) => ({ name: c, variance: data.pca.explained_variance[i] }))}>
                        <CartesianGrid strokeDasharray="3 3" stroke="#1F1F23" />
                        <XAxis dataKey="name" tick={{ fontSize: 11 }} stroke="#6B7280" />
                        <YAxis tick={{ fontSize: 10 }} stroke="#6B7280" unit="%" />
                        <Tooltip content={<ChartTooltip />} />
                        <Bar dataKey="variance" fill="#2563EB" radius={[6, 6, 0, 0]} name="Variance %" />
                    </BarChart>
                </ResponsiveContainer>
            </div>

            {/* Gate violations */}
            {data.summary.gate_violations.length > 0 && (
                <div className="bg-red-500/10 rounded-xl p-5 border border-red-500/20">
                    <h3 className="text-sm font-semibold uppercase tracking-wider text-red-400 mb-3 flex items-center gap-2">
                        <AlertTriangle className="w-4 h-4" /> Risk Gate Violations
                    </h3>
                    {data.summary.gate_violations.map((v, i) => (
                        <div key={i} className="text-sm text-red-300 mb-1">
                            <strong>{v.metric}</strong>: {typeof v.value === "number" ? v.value.toFixed(4) : v.value} ({v.rule} limit: {typeof v.limit === "number" ? v.limit.toFixed(4) : v.limit})
                        </div>
                    ))}
                </div>
            )}
        </div>
    );
}
