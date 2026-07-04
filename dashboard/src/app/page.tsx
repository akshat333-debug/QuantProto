"use client";

import { useState, useEffect, useCallback } from "react";
import { TrendingUp, RefreshCw, BarChart3, Activity, Shield, GitBranch, Zap, Crosshair, ShieldCheck, Gauge, Scale } from "lucide-react";
import type { AnalysisData, StressData } from "@/lib/types";
import { runAnalysis as apiRunAnalysis, runStressTest as apiRunStress, fetchScenarios } from "@/lib/api";
import { ThemeToggle } from "@/components/ui/ThemeToggle";
import { ErrorBanner } from "@/components/ui/ErrorBanner";
import { ExportPanel } from "@/components/ui/ExportPanel";
import { StrategyBuilder, type FactorWeights } from "@/components/ui/StrategyBuilder";
import { OverviewTab } from "@/components/tabs/OverviewTab";
import { PerformanceTab } from "@/components/tabs/PerformanceTab";
import { RiskTab } from "@/components/tabs/RiskTab";
import { RegimeTab } from "@/components/tabs/RegimeTab";
import { PortfolioTab } from "@/components/tabs/PortfolioTab";
import { StressTestTab } from "@/components/tabs/StressTestTab";
import { IntegrityTab } from "@/components/tabs/IntegrityTab";
import { ChatPanel } from "@/components/ui/ChatPanel";

/* ─── Tab definitions ─────────────────────────────────────────── */

const TABS = [
    { id: "overview", label: "Overview", icon: Activity },
    { id: "integrity", label: "Integrity Audit", icon: Crosshair },
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
    const [dataSource, setDataSource] = useState<"synthetic" | "live">("synthetic");
    const [startDate, setStartDate] = useState("2020-01-01");
    const [endDate, setEndDate] = useState("2024-01-01");
    const [factorWeights, setFactorWeights] = useState<FactorWeights>({
        momentum: 33, mean_reversion: 33, volatility: 34,
    });

    // Fetch available scenarios
    useEffect(() => {
        fetchScenarios().then((s) => { setScenarios(s); setScenario(s[0]); });
    }, []);

    // Validation
    const tickerList = tickers.split(",").map((t) => t.trim().toUpperCase()).filter(Boolean);
    const isValid = tickerList.length > 0 && tickerList.length <= 20 && nDays >= 10 && nDays <= 5000 && seed >= 0 && seed <= 999999;

    const runAnalysis = useCallback(async () => {
        if (!isValid) return;
        setLoading(true); setError(null);
        // Normalize weights to [0,1] for backend
        const total = factorWeights.momentum + factorWeights.mean_reversion + factorWeights.volatility;
        const normWeights = total > 0 ? {
            momentum: factorWeights.momentum / total,
            mean_reversion: factorWeights.mean_reversion / total,
            volatility: factorWeights.volatility / total,
        } : undefined;
        try {
            const json = await apiRunAnalysis({ tickers: tickerList, nDays, seed, dataSource, startDate, endDate, factorWeights: normWeights });
            setData(json); setActiveTab("overview");
        } catch (e) {
            setError(`Analysis failed: ${e instanceof Error ? e.message : "Unknown error"}. Check that the API server is running on port 9000.`);
        } finally { setLoading(false); }
    }, [isValid, tickerList, nDays, seed, dataSource, startDate, endDate, factorWeights]);

    const runStress = useCallback(async () => {
        setStressLoading(true); setError(null);
        try { setStress(await apiRunStress(scenario, seed)); }
        catch (e) { setError(`Stress test failed: ${e instanceof Error ? e.message : "Unknown error"}`); }
        finally { setStressLoading(false); }
    }, [scenario, seed]);

    /* ── Input field classes (shared) ──────────────────────────── */
    const inputClass = "w-full h-9 px-3 rounded-lg bg-gray-50 dark:bg-[#0E1522] border border-gray-200 dark:border-[#1B2536] text-sm focus:outline-none focus:border-blue-500/60 focus:ring-2 focus:ring-blue-500/20 transition-colors";
    const labelClass = "text-[11px] font-semibold uppercase tracking-wider text-gray-500 dark:text-gray-400 mb-1.5 block";

    return (
        <div className="min-h-screen">
            {/* Top Nav */}
            <header className="sticky top-0 z-50 bg-white/80 dark:bg-[#05070C]/75 backdrop-blur-xl border-b border-gray-200 dark:border-[#1B2536]">
                <div className="max-w-[1500px] mx-auto px-4 sm:px-6 h-14 flex items-center justify-between">
                    <div className="flex items-center gap-3 min-w-0">
                        <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-blue-500 to-violet-600 flex items-center justify-center shadow-lg shadow-blue-500/25 flex-shrink-0">
                            <ShieldCheck className="w-4 h-4 text-white" />
                        </div>
                        <div className="min-w-0">
                            <h1 className="text-[15px] font-bold leading-tight tracking-tight">QuantProto</h1>
                            <p className="text-[10px] text-gray-500 dark:text-gray-400 leading-tight uppercase tracking-widest hidden sm:block">Backtest-Integrity Auditor</p>
                        </div>
                    </div>
                    <div className="flex items-center gap-2">
                        {data && <ExportPanel data={data} />}
                        <ThemeToggle />
                    </div>
                </div>
            </header>

            <div className="max-w-[1500px] mx-auto px-4 sm:px-6 py-6">
                {error && <ErrorBanner message={error} onDismiss={() => setError(null)} />}

                <div className="flex flex-col lg:flex-row gap-6 items-start">
                    {/* ── Config sidebar ── */}
                    <aside className="w-full lg:w-[300px] lg:flex-shrink-0 lg:sticky lg:top-20 space-y-4">
                        <div className="panel-card bg-white dark:bg-[#0B111C] rounded-2xl border border-gray-200 dark:border-[#1B2536] p-5">
                            <div className="flex items-center gap-2 mb-4">
                                <Gauge className="w-4 h-4 text-blue-500" />
                                <h2 className="text-xs font-bold uppercase tracking-widest text-gray-600 dark:text-gray-300">Engine Setup</h2>
                            </div>
                            <div className="space-y-4">
                                <div>
                                    <label htmlFor="input-source" className={labelClass}>Data Source</label>
                                    <select id="input-source" value={dataSource} onChange={(e) => setDataSource(e.target.value as "synthetic" | "live")} className={inputClass}>
                                        <option value="synthetic">Synthetic</option>
                                        <option value="live">Live (Yahoo)</option>
                                    </select>
                                </div>
                                <div>
                                    <label htmlFor="input-tickers" className={labelClass}>Tickers</label>
                                    <input id="input-tickers" value={tickers} onChange={(e) => setTickers(e.target.value)} className={inputClass} placeholder="AAPL,GOOG,MSFT" />
                                    {tickerList.length === 0 && tickers.length > 0 && <p className="text-xs text-red-400 mt-1">Enter at least one valid ticker</p>}
                                </div>
                                {dataSource === "synthetic" ? (
                                    <div className="grid grid-cols-2 gap-3">
                                        <div>
                                            <label htmlFor="input-days" className={labelClass}>Days</label>
                                            <input id="input-days" type="number" value={nDays} min={10} max={5000} onChange={(e) => setNDays(Math.max(10, Math.min(5000, Number(e.target.value) || 10)))} className={inputClass} />
                                        </div>
                                        <div>
                                            <label htmlFor="input-seed" className={labelClass}>Seed</label>
                                            <input id="input-seed" type="number" value={seed} min={0} max={999999} onChange={(e) => setSeed(Math.max(0, Math.min(999999, Number(e.target.value) || 0)))} className={inputClass} />
                                        </div>
                                    </div>
                                ) : (
                                    <>
                                        <div className="grid grid-cols-2 gap-3">
                                            <div>
                                                <label htmlFor="input-start" className={labelClass}>Start</label>
                                                <input id="input-start" type="date" value={startDate} onChange={(e) => setStartDate(e.target.value)} className={inputClass} />
                                            </div>
                                            <div>
                                                <label htmlFor="input-end" className={labelClass}>End</label>
                                                <input id="input-end" type="date" value={endDate} onChange={(e) => setEndDate(e.target.value)} className={inputClass} />
                                            </div>
                                        </div>
                                        <div>
                                            <label htmlFor="input-seed" className={labelClass}>Seed</label>
                                            <input id="input-seed" type="number" value={seed} min={0} max={999999} onChange={(e) => setSeed(Math.max(0, Math.min(999999, Number(e.target.value) || 0)))} className={inputClass} />
                                        </div>
                                    </>
                                )}
                            </div>
                        </div>

                        {/* Strategy Builder */}
                        <StrategyBuilder weights={factorWeights} onChange={setFactorWeights} />

                        <button onClick={runAnalysis} disabled={loading || !isValid}
                            className="w-full h-11 rounded-xl bg-gradient-to-r from-blue-600 to-violet-600 hover:from-blue-500 hover:to-violet-500 text-white font-semibold text-sm flex items-center justify-center gap-2 transition-all shadow-lg shadow-blue-600/25 hover:shadow-blue-500/40 disabled:opacity-50 disabled:cursor-not-allowed disabled:shadow-none">
                            {loading ? <RefreshCw className="w-4 h-4 animate-spin" /> : <TrendingUp className="w-4 h-4" />}
                            {loading ? "Running…" : "Run Analysis"}
                        </button>
                    </aside>

                    {/* ── Main content ── */}
                    <main className="flex-1 min-w-0 w-full">
                        {!data ? (
                            <>
                                {/* Hero / empty state */}
                                <div className="relative overflow-hidden rounded-2xl border border-gray-200 dark:border-[#1B2536] bg-white dark:bg-[#0B111C] px-6 py-12 sm:py-16 mb-6 text-center">
                                    <div className="absolute inset-0 pointer-events-none bg-[radial-gradient(600px_200px_at_50%_-40px,rgba(59,130,246,0.12),transparent)]" />
                                    <div className="relative">
                                        <h2 className="text-2xl sm:text-3xl font-extrabold tracking-tight mb-3">
                                            Is your edge <span className="text-transparent bg-clip-text bg-gradient-to-r from-blue-400 to-violet-400">real</span> — or overfit?
                                        </h2>
                                        <p className="text-gray-500 dark:text-gray-400 text-sm max-w-lg mx-auto mb-8">
                                            Run the built-in research engine from the panel on the left, or paste any backtest below.
                                            One score. An honest verdict.
                                        </p>
                                        <div className="flex flex-wrap justify-center gap-3">
                                            {[
                                                { icon: Scale, label: "Deflated Sharpe", hint: "multiple-testing corrected" },
                                                { icon: Crosshair, label: "Overfit Probability", hint: "PBO via CSCV" },
                                                { icon: Zap, label: "Cost Break-even", hint: "where the edge dies" },
                                            ].map(({ icon: FIcon, label, hint }) => (
                                                <div key={label} className="flex items-center gap-2.5 px-4 py-2.5 rounded-xl bg-gray-50 dark:bg-[#0E1522] border border-gray-200 dark:border-[#1B2536] text-left">
                                                    <FIcon className="w-4 h-4 text-blue-500 flex-shrink-0" />
                                                    <div>
                                                        <div className="text-xs font-semibold">{label}</div>
                                                        <div className="text-[10px] text-gray-500">{hint}</div>
                                                    </div>
                                                </div>
                                            ))}
                                        </div>
                                    </div>
                                </div>
                                {/* Bring-your-own-backtest auditor — usable with no engine run */}
                                <IntegrityTab data={null} />
                            </>
                        ) : (
                            <>
                                {/* Tabs — ARIA compliant, scrollable on mobile */}
                                <div role="tablist" aria-label="Dashboard sections"
                                    className="flex gap-1 mb-6 overflow-x-auto p-1 rounded-xl bg-gray-100 dark:bg-[#0B111C] border border-gray-200 dark:border-[#1B2536] w-full sm:w-fit">
                                    {TABS.map(({ id, label, icon: Icon }) => (
                                        <button key={id} role="tab" aria-selected={activeTab === id} aria-controls={`panel-${id}`} id={`tab-${id}`}
                                            onClick={() => setActiveTab(id)}
                                            className={`flex items-center gap-1.5 px-3.5 py-2 rounded-lg text-xs sm:text-[13px] font-medium whitespace-nowrap transition-all ${activeTab === id
                                                ? "bg-white dark:bg-[#1B2536] text-gray-900 dark:text-white shadow-sm"
                                                : "text-gray-500 dark:text-gray-400 hover:text-gray-700 dark:hover:text-gray-200"}`}
                                        >
                                            <Icon className={`w-3.5 h-3.5 ${activeTab === id ? "text-blue-500" : ""}`} />{label}
                                        </button>
                                    ))}
                                </div>

                                {activeTab === "overview" && <OverviewTab data={data} />}
                                {activeTab === "integrity" && <IntegrityTab data={data} />}
                                {activeTab === "equity" && <PerformanceTab data={data} />}
                                {activeTab === "risk" && <RiskTab data={data} />}
                                {activeTab === "regime" && <RegimeTab data={data} />}
                                {activeTab === "portfolio" && <PortfolioTab data={data} />}
                                {activeTab === "stress" && <StressTestTab stress={stress} stressLoading={stressLoading} scenario={scenario} scenarios={scenarios} onScenarioChange={setScenario} onRunStress={runStress} />}
                            </>
                        )}
                    </main>
                </div>
            </div>

            {/* Floating AI Chat */}
            <ChatPanel data={data} />
        </div>
    );
}
