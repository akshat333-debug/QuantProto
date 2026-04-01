"use client";

import { Download } from "lucide-react";
import type { AnalysisData } from "@/lib/types";

function downloadFile(content: string, filename: string, type: string) {
    const blob = new Blob([content], { type });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = filename;
    a.click();
    URL.revokeObjectURL(url);
}

function toCSV(data: AnalysisData): string {
    const lines: string[] = [];

    // Summary metrics
    lines.push("Section,Metric,Value");
    const s = data.summary;
    lines.push(`Summary,Action,${s.action}`);
    lines.push(`Summary,Gate Passed,${s.gate_passed}`);
    lines.push(`Summary,Total Return %,${s.total_return}`);
    lines.push(`Summary,Sharpe,${s.sharpe}`);
    lines.push(`Summary,Sortino,${s.sortino}`);
    lines.push(`Summary,VaR 95%,${s.var_95}`);
    lines.push(`Summary,CVaR 95%,${s.cvar_95}`);
    lines.push(`Summary,Max Drawdown %,${s.max_drawdown}`);
    lines.push(`Summary,Calmar,${s.calmar}`);
    lines.push(`Summary,Pain Index %,${s.pain_index}`);
    lines.push(`Summary,Bootstrap CI Lower,${s.bootstrap_ci.lower}`);
    lines.push(`Summary,Bootstrap CI Upper,${s.bootstrap_ci.upper}`);
    lines.push("");

    // Assets
    lines.push("Ticker,Ann Return %,Ann Vol %,Sharpe,Max DD %,Latest Price");
    for (const a of data.assets) {
        lines.push(`${a.ticker},${a.annualised_return.toFixed(2)},${a.annualised_vol.toFixed(2)},${a.sharpe.toFixed(4)},${a.max_drawdown.toFixed(2)},${a.latest_price.toFixed(2)}`);
    }
    lines.push("");

    // Portfolio allocations
    lines.push("Ticker,Mean-Variance %,Risk Parity %,Max Sharpe %");
    for (let i = 0; i < data.portfolio.tickers.length; i++) {
        lines.push(`${data.portfolio.tickers[i]},${data.portfolio.mean_variance[i]},${data.portfolio.risk_parity[i]},${data.portfolio.max_sharpe[i]}`);
    }
    lines.push("");

    // Equity curve
    lines.push("Date,Equity");
    for (let i = 0; i < data.equity_curve.dates.length; i++) {
        lines.push(`${data.equity_curve.dates[i]},${data.equity_curve.values[i]}`);
    }

    return lines.join("\n");
}

export function ExportPanel({ data }: { data: AnalysisData }) {
    const timestamp = new Date().toISOString().slice(0, 10);

    return (
        <div className="flex items-center gap-2">
            <button
                onClick={() => downloadFile(toCSV(data), `quantproto-${timestamp}.csv`, "text/csv")}
                className="flex items-center gap-1.5 h-8 px-3 rounded-lg text-xs font-semibold bg-emerald-600/20 hover:bg-emerald-600/30 text-emerald-400 transition-colors"
                aria-label="Export CSV"
            >
                <Download className="w-3.5 h-3.5" /> CSV
            </button>
            <button
                onClick={() => downloadFile(JSON.stringify(data, null, 2), `quantproto-${timestamp}.json`, "application/json")}
                className="flex items-center gap-1.5 h-8 px-3 rounded-lg text-xs font-semibold bg-blue-600/20 hover:bg-blue-600/30 text-blue-400 transition-colors"
                aria-label="Export JSON"
            >
                <Download className="w-3.5 h-3.5" /> JSON
            </button>
        </div>
    );
}
