import { AreaChart, Area, BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Cell } from "recharts";
import type { AnalysisData } from "@/lib/types";
import { ChartTooltip } from "@/components/ui/ChartTooltip";

export function RegimeTab({ data }: { data: AnalysisData }) {
    return (
        <div role="tabpanel" id="panel-regime" aria-labelledby="tab-regime" className="space-y-6">
            <div className="bg-white dark:bg-[#0F0F12] rounded-xl p-5 border border-gray-200 dark:border-[#1F1F23]">
                <h3 className="text-sm font-semibold uppercase tracking-wider text-gray-500 dark:text-gray-400 mb-4">Regime States</h3>
                <ResponsiveContainer width="100%" height={120}>
                    <BarChart data={data.regime.dates.map((d, i) => ({
                        date: d,
                        state: 1,
                        fill: data.regime.states[i] === "BULL" ? "#059669" : data.regime.states[i] === "BEAR" ? "#DC2626" : "#D97706",
                    }))}>
                        <XAxis dataKey="date" tick={{ fontSize: 9 }} stroke="#6B7280" tickFormatter={(v: string) => v.slice(5)} interval={Math.floor(data.regime.dates.length / 8)} />
                        <Tooltip content={({ active, payload }) => {
                            if (!active || !payload?.length) return null;
                            const d = payload[0].payload;
                            const idx = data.regime.dates.indexOf(d.date);
                            return (
                                <div className="bg-white dark:bg-[#1A1A1E] border border-gray-200 dark:border-[#2A2A2E] rounded-lg px-3 py-2 shadow-xl text-xs">
                                    <p>{d.date}</p>
                                    <p className="font-bold">{data.regime.states[idx]}</p>
                                </div>
                            );
                        }} />
                        <Bar dataKey="state" radius={[2, 2, 0, 0]}>
                            {data.regime.dates.map((_, i) => (
                                <Cell key={i} fill={data.regime.states[i] === "BULL" ? "#059669" : data.regime.states[i] === "BEAR" ? "#DC2626" : "#D97706"} />
                            ))}
                        </Bar>
                    </BarChart>
                </ResponsiveContainer>
            </div>

            <div className="bg-white dark:bg-[#0F0F12] rounded-xl p-5 border border-gray-200 dark:border-[#1F1F23]">
                <h3 className="text-sm font-semibold uppercase tracking-wider text-gray-500 dark:text-gray-400 mb-4">Regime Confidence</h3>
                <ResponsiveContainer width="100%" height={200}>
                    <AreaChart data={data.regime.dates.map((d, i) => ({ date: d, confidence: data.regime.confidence[i] * 100 }))}>
                        <CartesianGrid strokeDasharray="3 3" stroke="#1F1F23" />
                        <XAxis dataKey="date" tick={{ fontSize: 10 }} stroke="#6B7280" tickFormatter={(v: string) => v.slice(5)} interval={Math.floor(data.regime.dates.length / 6)} />
                        <YAxis tick={{ fontSize: 10 }} stroke="#6B7280" unit="%" domain={[0, 100]} />
                        <Tooltip content={<ChartTooltip />} />
                        <Area type="monotone" dataKey="confidence" stroke="#D97706" fill="#D97706" fillOpacity={0.2} strokeWidth={2} name="Confidence %" />
                    </AreaChart>
                </ResponsiveContainer>
            </div>

            {/* Regime distribution */}
            <div className="grid grid-cols-3 gap-4">
                {(["BULL", "NEUTRAL", "BEAR"] as const).map((regime) => {
                    const count = data.regime.states.filter((s) => s === regime).length;
                    const pct = ((count / data.regime.states.length) * 100).toFixed(1);
                    const color = regime === "BULL" ? "text-emerald-500" : regime === "BEAR" ? "text-red-500" : "text-amber-500";
                    return (
                        <div key={regime} className="bg-white dark:bg-[#0F0F12] rounded-xl p-4 border border-gray-200 dark:border-[#1F1F23] text-center">
                            <div className={`text-2xl font-bold ${color}`}>{pct}%</div>
                            <div className="text-xs text-gray-500 dark:text-gray-400 mt-1">{regime} ({count} days)</div>
                        </div>
                    );
                })}
            </div>
        </div>
    );
}
