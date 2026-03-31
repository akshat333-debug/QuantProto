import { TrendingUp, TrendingDown, AlertTriangle, Target, Zap, RefreshCw } from "lucide-react";
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from "recharts";
import type { StressData } from "@/lib/types";
import { MetricCard } from "@/components/ui/MetricCard";
import { ChartTooltip } from "@/components/ui/ChartTooltip";

export function StressTestTab({ stress, stressLoading, scenario, scenarios, onScenarioChange, onRunStress }: {
    stress: StressData | null;
    stressLoading: boolean;
    scenario: string;
    scenarios: string[];
    onScenarioChange: (s: string) => void;
    onRunStress: () => void;
}) {
    return (
        <div role="tabpanel" id="panel-stress" aria-labelledby="tab-stress" className="space-y-6">
            <div className="bg-white dark:bg-[#0F0F12] rounded-xl p-4 border border-gray-200 dark:border-[#1F1F23]">
                <div className="flex flex-col sm:flex-row items-stretch sm:items-end gap-4">
                    <div className="sm:w-72">
                        <label htmlFor="input-scenario" className="text-xs font-semibold uppercase tracking-wider text-gray-500 dark:text-gray-400 mb-1 block">Scenario</label>
                        <select
                            id="input-scenario"
                            value={scenario}
                            onChange={(e) => onScenarioChange(e.target.value)}
                            className="w-full h-10 px-3 rounded-lg bg-gray-50 dark:bg-[#1A1A1E] border border-gray-200 dark:border-[#2A2A2E] text-sm"
                        >
                            {scenarios.map((s) => (
                                <option key={s} value={s}>{s.replace(/_/g, " ").replace(/\b\w/g, (c) => c.toUpperCase())}</option>
                            ))}
                        </select>
                    </div>
                    <button
                        onClick={onRunStress}
                        disabled={stressLoading}
                        className="h-10 px-6 rounded-lg bg-red-600 hover:bg-red-500 text-white font-semibold text-sm flex items-center justify-center gap-2 transition-colors disabled:opacity-50"
                    >
                        {stressLoading ? <RefreshCw className="w-4 h-4 animate-spin" /> : <Zap className="w-4 h-4" />}
                        Run Stress Test
                    </button>
                </div>
            </div>

            {stress && (
                <>
                    <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
                        <MetricCard label="Max Drawdown" value={`${stress.scenario.max_drawdown}%`} icon={TrendingDown} color="text-red-500" />
                        <MetricCard label="Total Return" value={`${stress.scenario.total_return}%`} icon={TrendingUp} color={stress.scenario.total_return >= 0 ? "text-emerald-500" : "text-red-500"} />
                        <MetricCard label="Worst Day" value={`${stress.scenario.worst_day}%`} icon={AlertTriangle} color="text-red-500" />
                        <MetricCard label="Prob. of Loss" value={`${stress.monte_carlo.prob_loss}%`} sub={`${stress.monte_carlo.p5.toFixed(2)} — ${stress.monte_carlo.p95.toFixed(2)}`} icon={Target} color="text-amber-500" />
                    </div>

                    <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                        <div className="bg-white dark:bg-[#0F0F12] rounded-xl p-5 border border-gray-200 dark:border-[#1F1F23]">
                            <h3 className="text-sm font-semibold uppercase tracking-wider text-gray-500 dark:text-gray-400 mb-4">Stress Scenario Equity</h3>
                            <ResponsiveContainer width="100%" height={250}>
                                <LineChart data={stress.scenario.equity.map((v, i) => ({ day: i, equity: v }))}>
                                    <CartesianGrid strokeDasharray="3 3" stroke="#1F1F23" />
                                    <XAxis dataKey="day" tick={{ fontSize: 10 }} stroke="#6B7280" />
                                    <YAxis tick={{ fontSize: 10 }} stroke="#6B7280" />
                                    <Tooltip content={<ChartTooltip />} />
                                    <Line type="monotone" dataKey="equity" stroke="#DC2626" strokeWidth={2} dot={false} name="Equity" />
                                </LineChart>
                            </ResponsiveContainer>
                        </div>

                        <div className="bg-white dark:bg-[#0F0F12] rounded-xl p-5 border border-gray-200 dark:border-[#1F1F23]">
                            <h3 className="text-sm font-semibold uppercase tracking-wider text-gray-500 dark:text-gray-400 mb-4">Monte Carlo Paths</h3>
                            <ResponsiveContainer width="100%" height={250}>
                                <LineChart>
                                    <CartesianGrid strokeDasharray="3 3" stroke="#1F1F23" />
                                    <XAxis dataKey="day" tick={{ fontSize: 10 }} stroke="#6B7280" type="number" domain={[0, stress.monte_carlo.paths[0]?.length || 126]} />
                                    <YAxis tick={{ fontSize: 10 }} stroke="#6B7280" />
                                    <Tooltip content={<ChartTooltip />} />
                                    {stress.monte_carlo.paths.map((path, i) => (
                                        <Line
                                            key={i}
                                            data={path.map((v, j) => ({ day: j, value: v }))}
                                            type="monotone"
                                            dataKey="value"
                                            stroke={`hsl(${220 + i * 15}, 70%, 50%)`}
                                            strokeWidth={1}
                                            dot={false}
                                            name={`Path ${i + 1}`}
                                            strokeOpacity={0.5}
                                        />
                                    ))}
                                </LineChart>
                            </ResponsiveContainer>
                        </div>
                    </div>
                </>
            )}

            {!stress && (
                <div className="flex items-center justify-center h-[40vh]">
                    <div className="text-center">
                        <Zap className="w-12 h-12 mx-auto mb-4 text-red-500/50" />
                        <p className="text-gray-500 dark:text-gray-400 text-sm">Select a scenario and click <strong>Run Stress Test</strong></p>
                    </div>
                </div>
            )}
        </div>
    );
}
