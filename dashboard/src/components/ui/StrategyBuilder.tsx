"use client";

import { Sliders } from "lucide-react";

export type FactorWeights = {
    momentum: number;
    mean_reversion: number;
    volatility: number;
};

const FACTOR_META: { key: keyof FactorWeights; label: string; color: string; track: string; description: string }[] = [
    { key: "momentum", label: "Momentum", color: "bg-blue-500", track: "#3B82F6", description: "Rate-of-change trend signal" },
    { key: "mean_reversion", label: "Mean Reversion", color: "bg-emerald-500", track: "#10B981", description: "Z-score vs rolling mean" },
    { key: "volatility", label: "Volatility", color: "bg-amber-500", track: "#F59E0B", description: "Rolling realized vol" },
];

export function StrategyBuilder({ weights, onChange }: {
    weights: FactorWeights;
    onChange: (w: FactorWeights) => void;
}) {
    const total = weights.momentum + weights.mean_reversion + weights.volatility;

    return (
        <div className="panel-card bg-white dark:bg-[#0B111C] rounded-2xl border border-gray-200 dark:border-[#1B2536] p-5">
            <div className="flex items-center gap-2 mb-4">
                <Sliders className="w-4 h-4 text-violet-500" />
                <h2 className="text-xs font-bold uppercase tracking-widest text-gray-600 dark:text-gray-300">Factor Weights</h2>
            </div>
            <div className="space-y-4">
                {FACTOR_META.map(({ key, label, color, track, description }) => {
                    const value = weights[key];
                    const pct = value; // slider range is 0-100
                    return (
                        <div key={key}>
                            <div className="flex items-center justify-between mb-1.5">
                                <div className="flex items-center gap-1.5">
                                    <span className={`w-2 h-2 rounded-full ${color}`} />
                                    <span className="text-xs font-medium">{label}</span>
                                </div>
                                <span className="text-xs font-bold font-mono text-gray-600 dark:text-gray-300 tabular-nums">{value}%</span>
                            </div>
                            <input
                                type="range"
                                min={0}
                                max={100}
                                value={value}
                                onChange={(e) => onChange({ ...weights, [key]: Number(e.target.value) })}
                                className="w-full"
                                style={{ background: `linear-gradient(to right, ${track} ${pct}%, var(--muted) ${pct}%)` }}
                                aria-label={`${label} weight`}
                            />
                            <p className="text-[10px] text-gray-400 dark:text-gray-500 mt-1">{description}</p>
                        </div>
                    );
                })}
            </div>
            {/* Visual bar showing proportions */}
            {total > 0 && (
                <div className="mt-4">
                    <div className="flex h-1.5 rounded-full overflow-hidden">
                        <div className="bg-blue-500 transition-all" style={{ width: `${(weights.momentum / total) * 100}%` }} />
                        <div className="bg-emerald-500 transition-all" style={{ width: `${(weights.mean_reversion / total) * 100}%` }} />
                        <div className="bg-amber-500 transition-all" style={{ width: `${(weights.volatility / total) * 100}%` }} />
                    </div>
                    <p className="text-[10px] text-gray-400 dark:text-gray-500 mt-1.5 text-right">
                        Sum {total.toFixed(0)}% → normalized to 100%
                    </p>
                </div>
            )}
        </div>
    );
}
