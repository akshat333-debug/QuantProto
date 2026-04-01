"use client";

import { useState, useEffect, useCallback } from "react";
import { TrendingUp, RefreshCw, BarChart3, Activity, Shield, GitBranch, Zap } from "lucide-react";
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
import { ChatPanel } from "@/components/ui/ChatPanel";

/* ─── Tab definitions ─────────────────────────────────────────── */

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
    const inputClass = "w-full h-10 px-3 rounded-lg bg-gray-50 dark:bg-[#1A1A1E] border border-gray-200 dark:border-[#2A2A2E] text-sm focus:outline-none focus:ring-2 focus:ring-blue-500/50";
    const labelClass = "text-xs font-semibold uppercase tracking-wider text-gray-500 dark:text-gray-400 mb-1 block";

    return (
        <div className="min-h-screen bg-white dark:bg-[#0A0A0D]">
            {/* Top Nav */}
            <header className="sticky top-0 z-50 bg-white/80 dark:bg-[#0A0A0D]/80 backdrop-blur-xl border-b border-gray-200 dark:border-[#1F1F23]">
                <div className="max-w-[1400px] mx-auto px-3 sm:px-6 h-14 sm:h-16 flex items-center justify-between">
                    <div className="flex items-center gap-2 sm:gap-3">
                        <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-blue-600 to-purple-600 flex items-center justify-center">
                            <BarChart3 className="w-4 h-4 text-white" />
                        </div>
                        <h1 className="text-base sm:text-lg font-bold">QuantProto</h1>
                    </div>
                    <div className="flex items-center gap-2">
                        {data && <ExportPanel data={data} />}
                        <ThemeToggle />
                    </div>
                </div>
            </header>

            <div className="max-w-[1400px] mx-auto px-3 sm:px-6 py-4 sm:py-6">
                {/* Config Bar */}
                <div className="bg-white dark:bg-[#0F0F12] rounded-xl border border-gray-200 dark:border-[#1F1F23] p-3 sm:p-4 mb-4 sm:mb-6">
                    <div className="flex flex-wrap items-end gap-3 sm:gap-4">
                        {/* Data source toggle */}
                        <div className="w-full sm:w-36">
                            <label htmlFor="input-source" className={labelClass}>Data Source</label>
                            <select id="input-source" value={dataSource} onChange={(e) => setDataSource(e.target.value as "synthetic" | "live")} className={inputClass}>
                                <option value="synthetic">Synthetic</option>
                                <option value="live">Live (Yahoo)</option>
                            </select>
                        </div>
                        <div className="flex-1 min-w-[160px]">
                            <label htmlFor="input-tickers" className={labelClass}>Tickers</label>
                            <input id="input-tickers" value={tickers} onChange={(e) => setTickers(e.target.value)} className={inputClass} placeholder="AAPL,GOOG,MSFT" />
                            {tickerList.length === 0 && tickers.length > 0 && <p className="text-xs text-red-400 mt-1">Enter at least one valid ticker</p>}
                        </div>
                        {dataSource === "synthetic" ? (
                            <div className="w-20 sm:w-32">
                                <label htmlFor="input-days" className={labelClass}>Days</label>
                                <input id="input-days" type="number" value={nDays} min={10} max={5000} onChange={(e) => setNDays(Math.max(10, Math.min(5000, Number(e.target.value) || 10)))} className={inputClass} />
                            </div>
                        ) : (
                            <>
                                <div className="w-[calc(50%-6px)] sm:w-36">
                                    <label htmlFor="input-start" className={labelClass}>Start</label>
                                    <input id="input-start" type="date" value={startDate} onChange={(e) => setStartDate(e.target.value)} className={inputClass} />
                                </div>
                                <div className="w-[calc(50%-6px)] sm:w-36">
                                    <label htmlFor="input-end" className={labelClass}>End</label>
                                    <input id="input-end" type="date" value={endDate} onChange={(e) => setEndDate(e.target.value)} className={inputClass} />
                                </div>
                            </>
                        )}
                        <div className="w-20 sm:w-24">
                            <label htmlFor="input-seed" className={labelClass}>Seed</label>
                            <input id="input-seed" type="number" value={seed} min={0} max={999999} onChange={(e) => setSeed(Math.max(0, Math.min(999999, Number(e.target.value) || 0)))} className={inputClass} />
                        </div>
                        <button onClick={runAnalysis} disabled={loading || !isValid} className="w-full sm:w-auto h-10 px-6 rounded-lg bg-blue-600 hover:bg-blue-500 text-white font-semibold text-sm flex items-center justify-center gap-2 transition-colors disabled:opacity-50 disabled:cursor-not-allowed">
                            {loading ? <RefreshCw className="w-4 h-4 animate-spin" /> : <TrendingUp className="w-4 h-4" />}
                            {loading ? "Running..." : "Run Analysis"}
                        </button>
                    </div>
                </div>

                {/* Strategy Builder */}
                <StrategyBuilder weights={factorWeights} onChange={setFactorWeights} />

                {error && <ErrorBanner message={error} onDismiss={() => setError(null)} />}

                {!data ? (
                    <div className="flex items-center justify-center h-[50vh] sm:h-[60vh]">
                        <div className="text-center px-4">
                            <div className="w-16 h-16 sm:w-20 sm:h-20 mx-auto mb-4 sm:mb-6 rounded-2xl bg-gradient-to-br from-blue-600/20 to-purple-600/20 flex items-center justify-center">
                                <BarChart3 className="w-8 h-8 sm:w-10 sm:h-10 text-blue-500" />
                            </div>
                            <h2 className="text-lg sm:text-xl font-bold mb-2">Run Analysis to See Results</h2>
                            <p className="text-gray-500 dark:text-gray-400 text-xs sm:text-sm max-w-md">
                                Configure tickers, time period, factor weights, and seed above, then click <strong>Run Analysis</strong>.
                            </p>
                        </div>
                    </div>
                ) : (
                    <>
                        {/* Tabs — ARIA compliant, scrollable on mobile */}
                        <div role="tablist" aria-label="Dashboard sections" className="flex gap-1 mb-4 sm:mb-6 overflow-x-auto pb-1 -mx-1 px-1">
                            {TABS.map(({ id, label, icon: Icon }) => (
                                <button key={id} role="tab" aria-selected={activeTab === id} aria-controls={`panel-${id}`} id={`tab-${id}`}
                                    onClick={() => setActiveTab(id)}
                                    className={`flex items-center gap-1.5 sm:gap-2 px-3 sm:px-4 py-2 rounded-lg text-xs sm:text-sm font-medium whitespace-nowrap transition-colors ${activeTab === id ? "bg-blue-600 text-white" : "text-gray-500 dark:text-gray-400 hover:bg-gray-100 dark:hover:bg-[#1F1F23]"}`}
                                >
                                    <Icon className="w-3.5 h-3.5 sm:w-4 sm:h-4" />{label}
                                </button>
                            ))}
                        </div>

                        {activeTab === "overview" && <OverviewTab data={data} />}
                        {activeTab === "equity" && <PerformanceTab data={data} />}
                        {activeTab === "risk" && <RiskTab data={data} />}
                        {activeTab === "regime" && <RegimeTab data={data} />}
                        {activeTab === "portfolio" && <PortfolioTab data={data} />}
                        {activeTab === "stress" && <StressTestTab stress={stress} stressLoading={stressLoading} scenario={scenario} scenarios={scenarios} onScenarioChange={setScenario} onRunStress={runStress} />}
                    </>
                )}
            </div>

            {/* Floating AI Chat */}
            <ChatPanel data={data} />
        </div>
    );
}
