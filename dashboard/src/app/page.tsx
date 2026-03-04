"use client";

import { useState, useEffect } from "react";
import { useTheme } from "next-themes";
import {
    Sun, Moon, Activity, TrendingUp, TrendingDown, Shield, BarChart3,
    AlertTriangle, ChevronDown, Play, Zap, PieChart, GitBranch,
    Target, Layers, RefreshCw,
} from "lucide-react";
import {
    LineChart, Line, AreaChart, Area, BarChart, Bar, XAxis, YAxis,
    CartesianGrid, Tooltip, ResponsiveContainer, RadarChart, Radar,
    PolarGrid, PolarAngleAxis, PolarRadiusAxis, Cell, PieChart as RPieChart,
    Pie,
} from "recharts";

const API = "http://localhost:9000";

type AnalysisData = {
    summary: {
        action: string; sharpe: number; sortino: number; var_95: number;
        cvar_95: number; max_drawdown: number; calmar: number; pain_index: number;
        total_return: number; n_splits: number; gate_passed: boolean;
        gate_violations: { metric: string; value: number; threshold: number }[];
        bootstrap_ci: { lower: number; upper: number; point: number };
    };
    equity_curve: { dates: string[]; values: number[] };
    drawdown: { dates: string[]; values: number[] };
    regime: { dates: string[]; states: string[]; confidence: number[] };
    portfolio: { tickers: string[]; mean_variance: number[]; risk_parity: number[]; max_sharpe: number[] };
    correlation: { tickers: string[]; matrix: number[][] };
    pca: { explained_variance: number[]; components: string[] };
    assets: { ticker: string; annualised_return: number; annualised_vol: number; sharpe: number; max_drawdown: number; latest_price: number }[];
    rolling_correlation: { dates: string[]; values: number[] };
};

type StressData = {
    scenario: { name: string; max_drawdown: number; total_return: number; worst_day: number; var_95: number; equity: number[] };
    monte_carlo: { median_terminal: number; p5: number; p95: number; prob_loss: number; worst_dd: number; paths: number[][] };
};

// ── Theme Toggle (deferred to avoid hydration mismatch) ──
function ThemeToggle() {
    const { theme, setTheme } = useTheme();
    const [mounted, setMounted] = useState(false);
    useEffect(() => setMounted(true), []);
    if (!mounted) return <div className="w-9 h-9" />; // placeholder to avoid layout shift
    return (
        <button
            onClick={() => setTheme(theme === "dark" ? "light" : "dark")}
            className="p-2 rounded-lg hover:bg-gray-100 dark:hover:bg-[#1F1F23] transition-colors"
        >
            {theme === "dark" ? <Sun className="w-5 h-5" /> : <Moon className="w-5 h-5" />}
        </button>
    );
}

// ── Metric Card ──
function MetricCard({ label, value, sub, icon: Icon, color = "text-gray-100" }: {
    label: string; value: string; sub?: string; icon: React.ElementType; color?: string;
}) {
    return (
        <div className="bg-white dark:bg-[#0F0F12] rounded-xl p-5 border border-gray-200 dark:border-[#1F1F23] hover:translate-y-[-2px] hover:shadow-lg transition-all duration-200">
            <div className="flex items-center justify-between mb-3">
                <span className="text-xs font-semibold uppercase tracking-wider text-gray-500 dark:text-gray-400">{label}</span>
                <Icon className={`w-4 h-4 ${color}`} />
            </div>
            <div className={`text-2xl font-bold ${color}`}>{value}</div>
            {sub && <div className="text-xs text-gray-500 dark:text-gray-400 mt-1">{sub}</div>}
        </div>
    );
}

// ── Decision Badge ──
function DecisionBadge({ action, passed }: { action: string; passed: boolean }) {
    return (
        <div className={`inline-flex items-center gap-2 px-4 py-2 rounded-full text-sm font-bold ${passed
            ? "bg-emerald-500/20 text-emerald-400 border border-emerald-500/30"
            : "bg-red-500/20 text-red-400 border border-red-500/30"
            }`}>
            {passed ? <Shield className="w-4 h-4" /> : <AlertTriangle className="w-4 h-4" />}
            {action}
        </div>
    );
}

// ── Custom Tooltip ──
function ChartTooltip({ active, payload, label }: any) {
    if (!active || !payload?.length) return null;
    return (
        <div className="bg-white dark:bg-[#1A1A1E] border border-gray-200 dark:border-[#2A2A2E] rounded-lg px-3 py-2 shadow-xl">
            <p className="text-xs text-gray-500 dark:text-gray-400 mb-1">{label}</p>
            {payload.map((p: any, i: number) => (
                <p key={i} className="text-sm font-semibold" style={{ color: p.color }}>
                    {p.name}: {typeof p.value === "number" ? p.value.toFixed(2) : p.value}
                </p>
            ))}
        </div>
    );
}

// ── Main Dashboard ──
export default function Dashboard() {
    const [data, setData] = useState<AnalysisData | null>(null);
    const [stress, setStress] = useState<StressData | null>(null);
    const [loading, setLoading] = useState(false);
    const [stressLoading, setStressLoading] = useState(false);
    const [activeTab, setActiveTab] = useState("overview");
    const [scenario, setScenario] = useState("2008_crisis");

    // Form state
    const [tickers, setTickers] = useState("AAPL,GOOG,MSFT,AMZN,META");
    const [nDays, setNDays] = useState(504);
    const [seed, setSeed] = useState(42);

    async function runAnalysis() {
        setLoading(true);
        try {
            const res = await fetch(`${API}/api/run-analysis`, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({
                    tickers: tickers.split(",").map((t) => t.trim()),
                    n_days: nDays,
                    seed,
                }),
            });
            const json = await res.json();
            setData(json);
            setActiveTab("overview");
        } catch (e) {
            console.error("Analysis failed:", e);
        }
        setLoading(false);
    }

    async function runStress() {
        setStressLoading(true);
        try {
            const res = await fetch(`${API}/api/stress-test`, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ scenario, seed }),
            });
            setStress(await res.json());
        } catch (e) {
            console.error("Stress test failed:", e);
        }
        setStressLoading(false);
    }

    const tabs = [
        { id: "overview", label: "Overview", icon: Activity },
        { id: "equity", label: "Performance", icon: TrendingUp },
        { id: "risk", label: "Risk", icon: Shield },
        { id: "regime", label: "Regime", icon: GitBranch },
        { id: "portfolio", label: "Portfolio", icon: PieChart },
        { id: "stress", label: "Stress Test", icon: Zap },
    ];

    return (
        <div className="min-h-screen bg-white dark:bg-[#0A0A0D]">
            {/* Top Nav */}
            <header className="sticky top-0 z-50 bg-white/80 dark:bg-[#0A0A0D]/80 backdrop-blur-xl border-b border-gray-200 dark:border-[#1F1F23]">
                <div className="max-w-[1400px] mx-auto px-4 sm:px-6 h-16 flex items-center justify-between">
                    <div className="flex items-center gap-3">
                        <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-blue-600 to-purple-600 flex items-center justify-center">
                            <BarChart3 className="w-4 h-4 text-white" />
                        </div>
                        <h1 className="text-lg font-bold">QuantProto</h1>
                    </div>
                    <div className="flex items-center gap-2">
                        <ThemeToggle />
                    </div>
                </div>
            </header>

            <div className="max-w-[1400px] mx-auto px-4 sm:px-6 py-6">
                {/* Config Bar */}
                <div className="bg-white dark:bg-[#0F0F12] rounded-xl border border-gray-200 dark:border-[#1F1F23] p-4 mb-6">
                    <div className="flex flex-wrap items-end gap-4">
                        <div className="flex-1 min-w-[200px]">
                            <label className="text-xs font-semibold uppercase tracking-wider text-gray-500 dark:text-gray-400 mb-1 block">Tickers</label>
                            <input
                                value={tickers}
                                onChange={(e) => setTickers(e.target.value)}
                                className="w-full h-10 px-3 rounded-lg bg-gray-50 dark:bg-[#1A1A1E] border border-gray-200 dark:border-[#2A2A2E] text-sm focus:outline-none focus:ring-2 focus:ring-blue-500/50"
                                placeholder="AAPL,GOOG,MSFT"
                            />
                        </div>
                        <div className="w-32">
                            <label className="text-xs font-semibold uppercase tracking-wider text-gray-500 dark:text-gray-400 mb-1 block">Days</label>
                            <input
                                type="number"
                                value={nDays}
                                onChange={(e) => setNDays(Number(e.target.value))}
                                className="w-full h-10 px-3 rounded-lg bg-gray-50 dark:bg-[#1A1A1E] border border-gray-200 dark:border-[#2A2A2E] text-sm focus:outline-none focus:ring-2 focus:ring-blue-500/50"
                            />
                        </div>
                        <div className="w-24">
                            <label className="text-xs font-semibold uppercase tracking-wider text-gray-500 dark:text-gray-400 mb-1 block">Seed</label>
                            <input
                                type="number"
                                value={seed}
                                onChange={(e) => setSeed(Number(e.target.value))}
                                className="w-full h-10 px-3 rounded-lg bg-gray-50 dark:bg-[#1A1A1E] border border-gray-200 dark:border-[#2A2A2E] text-sm focus:outline-none focus:ring-2 focus:ring-blue-500/50"
                            />
                        </div>
                        <button
                            onClick={runAnalysis}
                            disabled={loading}
                            className="h-10 px-6 rounded-lg bg-blue-600 hover:bg-blue-500 text-white font-semibold text-sm flex items-center gap-2 transition-colors disabled:opacity-50"
                        >
                            {loading ? <RefreshCw className="w-4 h-4 animate-spin" /> : <Play className="w-4 h-4" />}
                            {loading ? "Running..." : "Run Analysis"}
                        </button>
                    </div>
                </div>

                {!data ? (
                    <div className="flex items-center justify-center h-[60vh]">
                        <div className="text-center">
                            <div className="w-20 h-20 mx-auto mb-6 rounded-2xl bg-gradient-to-br from-blue-600/20 to-purple-600/20 flex items-center justify-center">
                                <BarChart3 className="w-10 h-10 text-blue-500" />
                            </div>
                            <h2 className="text-xl font-bold mb-2">Run Analysis to See Results</h2>
                            <p className="text-gray-500 dark:text-gray-400 text-sm max-w-md">
                                Configure your tickers, time period, and seed above, then click <strong>Run Analysis</strong> to
                                see equity curves, risk metrics, regime detection, portfolio optimisation, and more.
                            </p>
                        </div>
                    </div>
                ) : (
                    <>
                        {/* Tabs */}
                        <div className="flex gap-1 mb-6 overflow-x-auto pb-1">
                            {tabs.map(({ id, label, icon: Icon }) => (
                                <button
                                    key={id}
                                    onClick={() => setActiveTab(id)}
                                    className={`flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium whitespace-nowrap transition-colors ${activeTab === id
                                        ? "bg-blue-600 text-white"
                                        : "text-gray-500 dark:text-gray-400 hover:bg-gray-100 dark:hover:bg-[#1F1F23]"
                                        }`}
                                >
                                    <Icon className="w-4 h-4" />
                                    {label}
                                </button>
                            ))}
                        </div>

                        {/* Overview Tab */}
                        {activeTab === "overview" && (
                            <div className="space-y-6">
                                <div className="flex items-center gap-4 mb-2">
                                    <DecisionBadge action={data.summary.action} passed={data.summary.gate_passed} />
                                    <span className="text-sm text-gray-500 dark:text-gray-400">
                                        Sharpe 95% CI: [{data.summary.bootstrap_ci.lower}, {data.summary.bootstrap_ci.upper}]
                                    </span>
                                </div>

                                <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
                                    <MetricCard label="Total Return" value={`${data.summary.total_return > 0 ? "+" : ""}${data.summary.total_return}%`} icon={TrendingUp} color={data.summary.total_return >= 0 ? "text-emerald-500" : "text-red-500"} />
                                    <MetricCard label="Sharpe Ratio" value={data.summary.sharpe.toFixed(2)} sub="Annualised" icon={Target} color={data.summary.sharpe >= 1 ? "text-emerald-500" : data.summary.sharpe >= 0.5 ? "text-amber-500" : "text-red-500"} />
                                    <MetricCard label="Max Drawdown" value={`${data.summary.max_drawdown}%`} sub="Peak to trough" icon={TrendingDown} color="text-red-500" />
                                    <MetricCard label="VaR (95%)" value={`${data.summary.var_95}%`} sub="Daily" icon={Shield} color="text-amber-500" />
                                </div>

                                <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
                                    <MetricCard label="Sortino" value={data.summary.sortino.toFixed(2)} icon={Activity} color="text-blue-500" />
                                    <MetricCard label="CVaR (95%)" value={`${data.summary.cvar_95}%`} icon={AlertTriangle} color="text-red-500" />
                                    <MetricCard label="Calmar" value={data.summary.calmar.toFixed(2)} icon={Layers} color="text-purple-500" />
                                    <MetricCard label="Pain Index" value={`${data.summary.pain_index}%`} icon={Activity} color="text-amber-500" />
                                </div>

                                {/* Mini equity curve */}
                                <div className="bg-white dark:bg-[#0F0F12] rounded-xl p-5 border border-gray-200 dark:border-[#1F1F23]">
                                    <h3 className="text-sm font-semibold uppercase tracking-wider text-gray-500 dark:text-gray-400 mb-4">Equity Curve</h3>
                                    <ResponsiveContainer width="100%" height={250}>
                                        <AreaChart data={data.equity_curve.dates.map((d, i) => ({ date: d, value: data.equity_curve.values[i] }))}>
                                            <defs>
                                                <linearGradient id="eqGrad" x1="0" y1="0" x2="0" y2="1">
                                                    <stop offset="5%" stopColor="#2563EB" stopOpacity={0.3} />
                                                    <stop offset="95%" stopColor="#2563EB" stopOpacity={0} />
                                                </linearGradient>
                                            </defs>
                                            <CartesianGrid strokeDasharray="3 3" stroke="#1F1F23" />
                                            <XAxis dataKey="date" tick={{ fontSize: 10 }} stroke="#6B7280" tickFormatter={(v) => v.slice(5)} interval={Math.floor(data.equity_curve.dates.length / 8)} />
                                            <YAxis tick={{ fontSize: 10 }} stroke="#6B7280" domain={["auto", "auto"]} />
                                            <Tooltip content={<ChartTooltip />} />
                                            <Area type="monotone" dataKey="value" stroke="#2563EB" strokeWidth={2} fill="url(#eqGrad)" name="Equity" />
                                        </AreaChart>
                                    </ResponsiveContainer>
                                </div>

                                {/* Asset table */}
                                <div className="bg-white dark:bg-[#0F0F12] rounded-xl p-5 border border-gray-200 dark:border-[#1F1F23]">
                                    <h3 className="text-sm font-semibold uppercase tracking-wider text-gray-500 dark:text-gray-400 mb-4">Asset Breakdown</h3>
                                    <div className="overflow-x-auto">
                                        <table className="w-full text-sm">
                                            <thead>
                                                <tr className="text-left text-xs font-semibold uppercase tracking-wider text-gray-500 dark:text-gray-400 border-b border-gray-200 dark:border-[#1F1F23]">
                                                    <th className="pb-3 pr-4">Ticker</th>
                                                    <th className="pb-3 pr-4">Price</th>
                                                    <th className="pb-3 pr-4">Ann. Return</th>
                                                    <th className="pb-3 pr-4">Ann. Vol</th>
                                                    <th className="pb-3 pr-4">Sharpe</th>
                                                    <th className="pb-3">Max DD</th>
                                                </tr>
                                            </thead>
                                            <tbody>
                                                {data.assets.map((a) => (
                                                    <tr key={a.ticker} className="border-b border-gray-100 dark:border-[#1A1A1E] hover:bg-gray-50 dark:hover:bg-[#1A1A1E] transition-colors">
                                                        <td className="py-3 pr-4 font-semibold">{a.ticker}</td>
                                                        <td className="py-3 pr-4">${a.latest_price.toFixed(2)}</td>
                                                        <td className={`py-3 pr-4 font-medium ${a.annualised_return >= 0 ? "text-emerald-500" : "text-red-500"}`}>{a.annualised_return >= 0 ? "+" : ""}{a.annualised_return.toFixed(1)}%</td>
                                                        <td className="py-3 pr-4">{a.annualised_vol.toFixed(1)}%</td>
                                                        <td className={`py-3 pr-4 font-medium ${a.sharpe >= 1 ? "text-emerald-500" : a.sharpe >= 0 ? "text-amber-500" : "text-red-500"}`}>{a.sharpe.toFixed(2)}</td>
                                                        <td className="py-3 text-red-500">{a.max_drawdown.toFixed(1)}%</td>
                                                    </tr>
                                                ))}
                                            </tbody>
                                        </table>
                                    </div>
                                </div>
                            </div>
                        )}

                        {/* Performance Tab */}
                        {activeTab === "equity" && (
                            <div className="space-y-6">
                                <div className="bg-white dark:bg-[#0F0F12] rounded-xl p-5 border border-gray-200 dark:border-[#1F1F23]">
                                    <h3 className="text-sm font-semibold uppercase tracking-wider text-gray-500 dark:text-gray-400 mb-4">Equity Curve</h3>
                                    <ResponsiveContainer width="100%" height={350}>
                                        <AreaChart data={data.equity_curve.dates.map((d, i) => ({ date: d, equity: data.equity_curve.values[i] }))}>
                                            <defs>
                                                <linearGradient id="eqGrad2" x1="0" y1="0" x2="0" y2="1">
                                                    <stop offset="5%" stopColor="#059669" stopOpacity={0.3} />
                                                    <stop offset="95%" stopColor="#059669" stopOpacity={0} />
                                                </linearGradient>
                                            </defs>
                                            <CartesianGrid strokeDasharray="3 3" stroke="#1F1F23" />
                                            <XAxis dataKey="date" tick={{ fontSize: 10 }} stroke="#6B7280" tickFormatter={(v) => v.slice(5)} interval={Math.floor(data.equity_curve.dates.length / 10)} />
                                            <YAxis tick={{ fontSize: 10 }} stroke="#6B7280" domain={["auto", "auto"]} />
                                            <Tooltip content={<ChartTooltip />} />
                                            <Area type="monotone" dataKey="equity" stroke="#059669" strokeWidth={2} fill="url(#eqGrad2)" name="Equity" />
                                        </AreaChart>
                                    </ResponsiveContainer>
                                </div>

                                <div className="bg-white dark:bg-[#0F0F12] rounded-xl p-5 border border-gray-200 dark:border-[#1F1F23]">
                                    <h3 className="text-sm font-semibold uppercase tracking-wider text-gray-500 dark:text-gray-400 mb-4">Drawdown</h3>
                                    <ResponsiveContainer width="100%" height={250}>
                                        <AreaChart data={data.drawdown.dates.map((d, i) => ({ date: d, dd: data.drawdown.values[i] }))}>
                                            <defs>
                                                <linearGradient id="ddGrad" x1="0" y1="0" x2="0" y2="1">
                                                    <stop offset="5%" stopColor="#DC2626" stopOpacity={0.3} />
                                                    <stop offset="95%" stopColor="#DC2626" stopOpacity={0} />
                                                </linearGradient>
                                            </defs>
                                            <CartesianGrid strokeDasharray="3 3" stroke="#1F1F23" />
                                            <XAxis dataKey="date" tick={{ fontSize: 10 }} stroke="#6B7280" tickFormatter={(v) => v.slice(5)} interval={Math.floor(data.drawdown.dates.length / 10)} />
                                            <YAxis tick={{ fontSize: 10 }} stroke="#6B7280" unit="%" />
                                            <Tooltip content={<ChartTooltip />} />
                                            <Area type="monotone" dataKey="dd" stroke="#DC2626" strokeWidth={2} fill="url(#ddGrad)" name="Drawdown %" />
                                        </AreaChart>
                                    </ResponsiveContainer>
                                </div>
                            </div>
                        )}

                        {/* Risk Tab */}
                        {activeTab === "risk" && (
                            <div className="space-y-6">
                                <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                                    <div className="bg-white dark:bg-[#0F0F12] rounded-xl p-5 border border-gray-200 dark:border-[#1F1F23]">
                                        <h3 className="text-sm font-semibold uppercase tracking-wider text-gray-500 dark:text-gray-400 mb-4">Correlation Matrix</h3>
                                        <div className="overflow-x-auto">
                                            <table className="w-full text-xs">
                                                <thead>
                                                    <tr>
                                                        <th className="pb-2"></th>
                                                        {data.correlation.tickers.map((t) => (
                                                            <th key={t} className="pb-2 px-2 font-semibold">{t}</th>
                                                        ))}
                                                    </tr>
                                                </thead>
                                                <tbody>
                                                    {data.correlation.tickers.map((t, i) => (
                                                        <tr key={t}>
                                                            <td className="py-1 pr-2 font-semibold">{t}</td>
                                                            {data.correlation.matrix[i].map((v, j) => (
                                                                <td key={j} className="py-1 px-2 text-center" style={{
                                                                    backgroundColor: `rgba(${v > 0 ? "5,150,105" : "220,38,38"}, ${Math.abs(v) * 0.4})`,
                                                                    borderRadius: "4px",
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
                                                <XAxis dataKey="date" tick={{ fontSize: 10 }} stroke="#6B7280" tickFormatter={(v) => v.slice(5)} interval={Math.floor(data.rolling_correlation.dates.length / 6)} />
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
                                                <strong>{v.metric}</strong>: {v.value.toFixed(4)} (threshold: {v.threshold})
                                            </div>
                                        ))}
                                    </div>
                                )}
                            </div>
                        )}

                        {/* Regime Tab */}
                        {activeTab === "regime" && (
                            <div className="space-y-6">
                                <div className="bg-white dark:bg-[#0F0F12] rounded-xl p-5 border border-gray-200 dark:border-[#1F1F23]">
                                    <h3 className="text-sm font-semibold uppercase tracking-wider text-gray-500 dark:text-gray-400 mb-4">Regime States</h3>
                                    <ResponsiveContainer width="100%" height={200}>
                                        <BarChart data={data.regime.dates.map((d, i) => ({
                                            date: d,
                                            value: data.regime.states[i] === "BULL" ? 1 : data.regime.states[i] === "NEUTRAL" ? 0 : -1,
                                            state: data.regime.states[i],
                                        }))}>
                                            <CartesianGrid strokeDasharray="3 3" stroke="#1F1F23" />
                                            <XAxis dataKey="date" tick={{ fontSize: 10 }} stroke="#6B7280" tickFormatter={(v) => v.slice(5)} interval={Math.floor(data.regime.dates.length / 8)} />
                                            <YAxis tick={{ fontSize: 10 }} stroke="#6B7280" domain={[-1.5, 1.5]} ticks={[-1, 0, 1]} tickFormatter={(v: number) => v === 1 ? "BULL" : v === 0 ? "NEUTRAL" : "BEAR"} />
                                            <Tooltip content={<ChartTooltip />} />
                                            <Bar dataKey="value" name="Regime">
                                                {data.regime.dates.map((_, i) => (
                                                    <Cell key={i} fill={data.regime.states[i] === "BULL" ? "#059669" : data.regime.states[i] === "NEUTRAL" ? "#D97706" : "#DC2626"} />
                                                ))}
                                            </Bar>
                                        </BarChart>
                                    </ResponsiveContainer>
                                </div>

                                <div className="bg-white dark:bg-[#0F0F12] rounded-xl p-5 border border-gray-200 dark:border-[#1F1F23]">
                                    <h3 className="text-sm font-semibold uppercase tracking-wider text-gray-500 dark:text-gray-400 mb-4">Regime Confidence</h3>
                                    <ResponsiveContainer width="100%" height={200}>
                                        <AreaChart data={data.regime.dates.map((d, i) => ({ date: d, confidence: data.regime.confidence[i] * 100 }))}>
                                            <defs>
                                                <linearGradient id="confGrad" x1="0" y1="0" x2="0" y2="1">
                                                    <stop offset="5%" stopColor="#D97706" stopOpacity={0.3} />
                                                    <stop offset="95%" stopColor="#D97706" stopOpacity={0} />
                                                </linearGradient>
                                            </defs>
                                            <CartesianGrid strokeDasharray="3 3" stroke="#1F1F23" />
                                            <XAxis dataKey="date" tick={{ fontSize: 10 }} stroke="#6B7280" tickFormatter={(v) => v.slice(5)} interval={Math.floor(data.regime.dates.length / 8)} />
                                            <YAxis tick={{ fontSize: 10 }} stroke="#6B7280" unit="%" domain={[0, 100]} />
                                            <Tooltip content={<ChartTooltip />} />
                                            <Area type="monotone" dataKey="confidence" stroke="#D97706" strokeWidth={2} fill="url(#confGrad)" name="Confidence %" />
                                        </AreaChart>
                                    </ResponsiveContainer>
                                </div>

                                <div className="grid grid-cols-3 gap-4">
                                    {["BULL", "NEUTRAL", "BEAR"].map((state) => {
                                        const count = data.regime.states.filter((s) => s === state).length;
                                        const pct = ((count / data.regime.states.length) * 100).toFixed(1);
                                        const color = state === "BULL" ? "text-emerald-500" : state === "NEUTRAL" ? "text-amber-500" : "text-red-500";
                                        return (
                                            <div key={state} className="bg-white dark:bg-[#0F0F12] rounded-xl p-5 border border-gray-200 dark:border-[#1F1F23] text-center">
                                                <div className={`text-2xl font-bold ${color}`}>{pct}%</div>
                                                <div className="text-xs text-gray-500 dark:text-gray-400 mt-1">{state} ({count} days)</div>
                                            </div>
                                        );
                                    })}
                                </div>
                            </div>
                        )}

                        {/* Portfolio Tab */}
                        {activeTab === "portfolio" && (
                            <div className="space-y-6">
                                <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
                                    {[
                                        { name: "Mean-Variance", weights: data.portfolio.mean_variance, color: "#2563EB" },
                                        { name: "Risk Parity", weights: data.portfolio.risk_parity, color: "#059669" },
                                        { name: "Max Sharpe", weights: data.portfolio.max_sharpe, color: "#9333EA" },
                                    ].map(({ name, weights, color }) => (
                                        <div key={name} className="bg-white dark:bg-[#0F0F12] rounded-xl p-5 border border-gray-200 dark:border-[#1F1F23]">
                                            <h3 className="text-sm font-semibold uppercase tracking-wider text-gray-500 dark:text-gray-400 mb-4">{name}</h3>
                                            <ResponsiveContainer width="100%" height={200}>
                                                <RPieChart>
                                                    <Pie
                                                        data={data.portfolio.tickers.map((t, i) => ({ name: t, value: weights[i] }))}
                                                        cx="50%" cy="50%" innerRadius={50} outerRadius={80}
                                                        dataKey="value" nameKey="name" label={({ name, value }) => `${name}: ${value}%`}
                                                    >
                                                        {data.portfolio.tickers.map((_, i) => (
                                                            <Cell key={i} fill={["#2563EB", "#059669", "#9333EA", "#DC2626", "#D97706", "#6366F1", "#EC4899"][i % 7]} />
                                                        ))}
                                                    </Pie>
                                                    <Tooltip />
                                                </RPieChart>
                                            </ResponsiveContainer>
                                        </div>
                                    ))}
                                </div>

                                <div className="bg-white dark:bg-[#0F0F12] rounded-xl p-5 border border-gray-200 dark:border-[#1F1F23]">
                                    <h3 className="text-sm font-semibold uppercase tracking-wider text-gray-500 dark:text-gray-400 mb-4">Allocation Comparison</h3>
                                    <ResponsiveContainer width="100%" height={300}>
                                        <BarChart data={data.portfolio.tickers.map((t, i) => ({
                                            ticker: t,
                                            "Mean-Variance": data.portfolio.mean_variance[i],
                                            "Risk Parity": data.portfolio.risk_parity[i],
                                            "Max Sharpe": data.portfolio.max_sharpe[i],
                                        }))}>
                                            <CartesianGrid strokeDasharray="3 3" stroke="#1F1F23" />
                                            <XAxis dataKey="ticker" tick={{ fontSize: 11 }} stroke="#6B7280" />
                                            <YAxis tick={{ fontSize: 10 }} stroke="#6B7280" unit="%" />
                                            <Tooltip content={<ChartTooltip />} />
                                            <Bar dataKey="Mean-Variance" fill="#2563EB" radius={[4, 4, 0, 0]} />
                                            <Bar dataKey="Risk Parity" fill="#059669" radius={[4, 4, 0, 0]} />
                                            <Bar dataKey="Max Sharpe" fill="#9333EA" radius={[4, 4, 0, 0]} />
                                        </BarChart>
                                    </ResponsiveContainer>
                                </div>
                            </div>
                        )}

                        {/* Stress Test Tab */}
                        {activeTab === "stress" && (
                            <div className="space-y-6">
                                <div className="bg-white dark:bg-[#0F0F12] rounded-xl p-4 border border-gray-200 dark:border-[#1F1F23]">
                                    <div className="flex items-end gap-4">
                                        <div className="flex-1">
                                            <label className="text-xs font-semibold uppercase tracking-wider text-gray-500 dark:text-gray-400 mb-1 block">Scenario</label>
                                            <select
                                                value={scenario}
                                                onChange={(e) => setScenario(e.target.value)}
                                                className="w-full h-10 px-3 rounded-lg bg-gray-50 dark:bg-[#1A1A1E] border border-gray-200 dark:border-[#2A2A2E] text-sm"
                                            >
                                                <option value="2008_crisis">2008 Financial Crisis</option>
                                                <option value="covid_crash">COVID Crash</option>
                                                <option value="dotcom_bust">Dot-com Bust</option>
                                                <option value="flash_crash">Flash Crash</option>
                                                <option value="rate_hike">Rate Hike</option>
                                            </select>
                                        </div>
                                        <button
                                            onClick={runStress}
                                            disabled={stressLoading}
                                            className="h-10 px-6 rounded-lg bg-red-600 hover:bg-red-500 text-white font-semibold text-sm flex items-center gap-2 transition-colors disabled:opacity-50"
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
                        )}
                    </>
                )}
            </div>
        </div>
    );
}
