"use client";

import { useState, useEffect, useCallback } from "react";
import { useTheme } from "next-themes";
import {
    Sun, Moon, Activity, TrendingUp, TrendingDown, Shield,
    AlertTriangle, Zap, GitBranch,
    Target, Layers, RefreshCw, BarChart3,
} from "lucide-react";
import {
    LineChart, Line, AreaChart, Area, BarChart, Bar, XAxis, YAxis,
    CartesianGrid, Tooltip, ResponsiveContainer, Legend, Cell,
    PieChart as RPieChart, Pie,
} from "recharts";

/* ─── Types ───────────────────────────────────────────────────────── */

type GateViolation = { metric: string; value: number; rule: string; limit: number };
type BootstrapCI = { lower: number; upper: number; point: number };

type AnalysisData = {
    summary: {
        action: string; sharpe: number; sortino: number; var_95: number;
        cvar_95: number; max_drawdown: number; calmar: number; pain_index: number;
        total_return: number; n_splits: number; gate_passed: boolean;
        gate_violations: GateViolation[];
        bootstrap_ci: BootstrapCI;
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

type TooltipPayload = { color: string; name: string; value: number | string };

/* ─── Theme Toggle (deferred to avoid hydration mismatch) ─────── */

function ThemeToggle() {
    const { theme, setTheme } = useTheme();
    const [mounted, setMounted] = useState(false);
    useEffect(() => setMounted(true), []);
    if (!mounted) return <div className="w-9 h-9" />;
    return (
        <button
            onClick={() => setTheme(theme === "dark" ? "light" : "dark")}
            className="p-2 rounded-lg hover:bg-gray-100 dark:hover:bg-[#1F1F23] transition-colors"
            aria-label="Toggle theme"
        >
            {theme === "dark" ? <Sun className="w-5 h-5" /> : <Moon className="w-5 h-5" />}
        </button>
    );
}

/* ─── Metric Card ─────────────────────────────────────────────── */

function MetricCard({ label, value, sub, icon: Icon, color = "text-gray-100" }: {
    label: string; value: string; sub?: string; icon: React.ElementType; color?: string;
}) {
    return (
        <div className="bg-white dark:bg-[#0F0F12] rounded-xl p-4 sm:p-5 border border-gray-200 dark:border-[#1F1F23] hover:translate-y-[-2px] hover:shadow-lg transition-all duration-200 min-w-0">
            <div className="flex items-center justify-between mb-2">
                <span className="text-[10px] sm:text-xs font-semibold uppercase tracking-wider text-gray-500 dark:text-gray-400 truncate mr-2">{label}</span>
                <Icon className={`w-4 h-4 flex-shrink-0 ${color}`} />
            </div>
            <div className={`text-lg sm:text-2xl font-bold truncate ${color}`}>{value}</div>
            {sub && <div className="text-[10px] sm:text-xs text-gray-500 dark:text-gray-400 mt-1 truncate">{sub}</div>}
        </div>
    );
}

/* ─── Decision Badge ──────────────────────────────────────────── */

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

/* ─── Custom Tooltip (properly typed) ─────────────────────────── */

function ChartTooltip({ active, payload, label }: {
    active?: boolean;
    payload?: TooltipPayload[];
    label?: string | number;
}) {
    if (!active || !payload?.length) return null;
    return (
        <div className="bg-white dark:bg-[#1A1A1E] border border-gray-200 dark:border-[#2A2A2E] rounded-lg px-3 py-2 shadow-xl">
            <p className="text-xs text-gray-500 dark:text-gray-400 mb-1">{label}</p>
            {payload.map((p, i) => (
                <p key={i} className="text-sm font-semibold" style={{ color: p.color }}>
                    {p.name}: {typeof p.value === "number" ? p.value.toFixed(2) : p.value}
                </p>
            ))}
        </div>
    );
}

/* ─── Error Banner ────────────────────────────────────────────── */

function ErrorBanner({ message, onDismiss }: { message: string; onDismiss: () => void }) {
    return (
        <div className="bg-red-500/10 border border-red-500/30 rounded-xl p-4 mb-4 flex items-start gap-3">
            <AlertTriangle className="w-5 h-5 text-red-400 flex-shrink-0 mt-0.5" />
            <div className="flex-1">
                <p className="text-sm font-semibold text-red-400">Analysis Failed</p>
                <p className="text-xs text-red-300 mt-1">{message}</p>
            </div>
            <button onClick={onDismiss} className="text-red-400 hover:text-red-300 text-sm font-bold" aria-label="Dismiss error">✕</button>
        </div>
    );
}

/* ─── Constants ───────────────────────────────────────────────── */

const PIE_COLORS = ["#2563EB", "#059669", "#9333EA", "#DC2626", "#D97706", "#6366F1", "#EC4899"];

const TABS = [
    { id: "overview", label: "Overview", icon: Activity },
    { id: "equity", label: "Performance", icon: TrendingUp },
    { id: "risk", label: "Risk", icon: Shield },
    { id: "regime", label: "Regime", icon: GitBranch },
    { id: "portfolio", label: "Portfolio", icon: BarChart3 },
    { id: "stress", label: "Stress Test", icon: Zap },
] as const;

/* ─── Main Dashboard ──────────────────────────────────────────── */

export default function Dashboard() {
    const [data, setData] = useState<AnalysisData | null>(null);
    const [stress, setStress] = useState<StressData | null>(null);
    const [loading, setLoading] = useState(false);
    const [stressLoading, setStressLoading] = useState(false);
    const [activeTab, setActiveTab] = useState("overview");
    const [scenario, setScenario] = useState("2008_crisis");
    const [error, setError] = useState<string | null>(null);
    const [scenarios, setScenarios] = useState<string[]>([]);

    // Form state
    const [tickers, setTickers] = useState("AAPL,GOOG,MSFT,AMZN,META");
    const [nDays, setNDays] = useState(504);
    const [seed, setSeed] = useState(42);

    // Fetch available scenarios from backend
    useEffect(() => {
        fetch("/api/scenarios")
            .then((r) => r.json())
            .then((d: { scenarios: string[] }) => {
                if (d.scenarios?.length) {
                    setScenarios(d.scenarios);
                    setScenario(d.scenarios[0]);
                }
            })
            .catch(() => {
                // Fallback hardcoded if backend unreachable
                setScenarios(["2008_crisis", "covid_crash", "dotcom_bust", "flash_crash", "rate_hike"]);
            });
    }, []);

    // Validation helpers
    const tickerList = tickers.split(",").map((t) => t.trim().toUpperCase()).filter(Boolean);
    const isValid = tickerList.length > 0 && tickerList.length <= 20 && nDays >= 10 && nDays <= 5000 && seed >= 0 && seed <= 999999;

    const runAnalysis = useCallback(async () => {
        if (!isValid) return;
        setLoading(true);
        setError(null);
        try {
            const res = await fetch("/api/run-analysis", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ tickers: tickerList, n_days: nDays, seed }),
            });
            if (!res.ok) {
                const errBody = await res.json().catch(() => ({ detail: res.statusText }));
                throw new Error(errBody.detail || `HTTP ${res.status}`);
            }
            const json: AnalysisData = await res.json();
            setData(json);
            setActiveTab("overview");
        } catch (e) {
            const msg = e instanceof Error ? e.message : "Unknown error";
            setError(`Analysis failed: ${msg}. Check that the API server is running on port 9000.`);
        } finally {
            setLoading(false);
        }
    }, [isValid, tickerList, nDays, seed]);

    const runStress = useCallback(async () => {
        setStressLoading(true);
        setError(null);
        try {
            const res = await fetch("/api/stress-test", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ scenario, seed }),
            });
            if (!res.ok) {
                const errBody = await res.json().catch(() => ({ detail: res.statusText }));
                throw new Error(errBody.detail || `HTTP ${res.status}`);
            }
            setStress(await res.json());
        } catch (e) {
            const msg = e instanceof Error ? e.message : "Unknown error";
            setError(`Stress test failed: ${msg}`);
        } finally {
            setStressLoading(false);
        }
    }, [scenario, seed]);

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
                            <label htmlFor="input-tickers" className="text-xs font-semibold uppercase tracking-wider text-gray-500 dark:text-gray-400 mb-1 block">Tickers</label>
                            <input
                                id="input-tickers"
                                value={tickers}
                                onChange={(e) => setTickers(e.target.value)}
                                className="w-full h-10 px-3 rounded-lg bg-gray-50 dark:bg-[#1A1A1E] border border-gray-200 dark:border-[#2A2A2E] text-sm focus:outline-none focus:ring-2 focus:ring-blue-500/50"
                                placeholder="AAPL,GOOG,MSFT"
                            />
                            {tickerList.length === 0 && tickers.length > 0 && (
                                <p className="text-xs text-red-400 mt-1">Enter at least one valid ticker</p>
                            )}
                        </div>
                        <div className="w-32">
                            <label htmlFor="input-days" className="text-xs font-semibold uppercase tracking-wider text-gray-500 dark:text-gray-400 mb-1 block">Days</label>
                            <input
                                id="input-days"
                                type="number"
                                value={nDays}
                                min={10}
                                max={5000}
                                onChange={(e) => setNDays(Math.max(10, Math.min(5000, Number(e.target.value) || 10)))}
                                className="w-full h-10 px-3 rounded-lg bg-gray-50 dark:bg-[#1A1A1E] border border-gray-200 dark:border-[#2A2A2E] text-sm focus:outline-none focus:ring-2 focus:ring-blue-500/50"
                            />
                        </div>
                        <div className="w-24">
                            <label htmlFor="input-seed" className="text-xs font-semibold uppercase tracking-wider text-gray-500 dark:text-gray-400 mb-1 block">Seed</label>
                            <input
                                id="input-seed"
                                type="number"
                                value={seed}
                                min={0}
                                max={999999}
                                onChange={(e) => setSeed(Math.max(0, Math.min(999999, Number(e.target.value) || 0)))}
                                className="w-full h-10 px-3 rounded-lg bg-gray-50 dark:bg-[#1A1A1E] border border-gray-200 dark:border-[#2A2A2E] text-sm focus:outline-none focus:ring-2 focus:ring-blue-500/50"
                            />
                        </div>
                        <button
                            onClick={runAnalysis}
                            disabled={loading || !isValid}
                            className="h-10 px-6 rounded-lg bg-blue-600 hover:bg-blue-500 text-white font-semibold text-sm flex items-center gap-2 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
                        >
                            {loading ? <RefreshCw className="w-4 h-4 animate-spin" /> : <TrendingUp className="w-4 h-4" />}
                            {loading ? "Running..." : "Run Analysis"}
                        </button>
                    </div>
                </div>

                {/* Error Banner */}
                {error && <ErrorBanner message={error} onDismiss={() => setError(null)} />}

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
                        {/* Tabs — ARIA compliant */}
                        <div role="tablist" aria-label="Dashboard sections" className="flex gap-1 mb-6 overflow-x-auto pb-1">
                            {TABS.map(({ id, label, icon: Icon }) => (
                                <button
                                    key={id}
                                    role="tab"
                                    aria-selected={activeTab === id}
                                    aria-controls={`panel-${id}`}
                                    id={`tab-${id}`}
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
                        )}

                        {/* Performance Tab */}
                        {activeTab === "equity" && (
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
                        )}

                        {/* Risk Tab */}
                        {activeTab === "risk" && (
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
                        )}

                        {/* Regime Tab */}
                        {activeTab === "regime" && (
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
                        )}

                        {/* Portfolio Tab */}
                        {activeTab === "portfolio" && (() => {
                            // Build pie data with "Other" bucket for small allocations
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
                        })()}

                        {/* Stress Test Tab */}
                        {activeTab === "stress" && (
                            <div role="tabpanel" id="panel-stress" aria-labelledby="tab-stress" className="space-y-6">
                                <div className="bg-white dark:bg-[#0F0F12] rounded-xl p-4 border border-gray-200 dark:border-[#1F1F23]">
                                    <div className="flex flex-col sm:flex-row items-stretch sm:items-end gap-4">
                                        <div className="sm:w-72">
                                            <label htmlFor="input-scenario" className="text-xs font-semibold uppercase tracking-wider text-gray-500 dark:text-gray-400 mb-1 block">Scenario</label>
                                            <select
                                                id="input-scenario"
                                                value={scenario}
                                                onChange={(e) => setScenario(e.target.value)}
                                                className="w-full h-10 px-3 rounded-lg bg-gray-50 dark:bg-[#1A1A1E] border border-gray-200 dark:border-[#2A2A2E] text-sm"
                                            >
                                                {scenarios.map((s) => (
                                                    <option key={s} value={s}>{s.replace(/_/g, " ").replace(/\b\w/g, (c) => c.toUpperCase())}</option>
                                                ))}
                                            </select>
                                        </div>
                                        <button
                                            onClick={runStress}
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
                        )}
                    </>
                )}
            </div>
        </div>
    );
}
