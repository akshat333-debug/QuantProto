"use client";

import { Sliders } from "lucide-react";

export type FactorWeights = {
    momentum: number;
    mean_reversion: number;
    volatility: number;
};

const FACTOR_META: { key: keyof FactorWeights; label: string; color: string; description: string }[] = [
    { key: "momentum", label: "Momentum", color: "bg-blue-500", description: "Rate-of-change trend signal" },
    { key: "mean_reversion", label: "Mean Reversion", color: "bg-emerald-500", description: "Z-score vs rolling mean" },
    { key: "volatility", label: "Volatility", color: "bg-amber-500", description: "Rolling realized vol" },
];

export function StrategyBuilder({ weights, onChange }: {
    weights: FactorWeights;
    onChange: (w: FactorWeights) => void;
}) {
    const total = weights.momentum + weights.mean_reversion + weights.volatility;

    return (
        <div className="bg-white dark:bg-[#0F0F12] rounded-xl border border-gray-200 dark:border-[#1F1F23] p-4 mb-6">
            <div className="flex items-center gap-2 mb-3">
                <Sliders className="w-4 h-4 text-purple-500" />
                <span className="text-xs font-semibold uppercase tracking-wider text-gray-500 dark:text-gray-400">Factor Weights</span>
                <span className="ml-auto text-[10px] text-gray-400">
                    Sum: {total.toFixed(0)}% → normalized to 100%
                </span>
            </div>
            <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
                {FACTOR_META.map(({ key, label, color, description }) => {
                    const value = weights[key];
                    return (
                        <div key={key}>
                            <div className="flex items-center justify-between mb-1">
                                <div className="flex items-center gap-1.5">
                                    <span className={`w-2 h-2 rounded-full ${color}`} />
                                    <span className="text-xs font-medium">{label}</span>
                                </div>
                                <span className="text-xs font-bold text-gray-600 dark:text-gray-300">{value}%</span>
                            </div>
                            <input
                                type="range"
                                min={0}
                                max={100}
                                value={value}
                                onChange={(e) => onChange({ ...weights, [key]: Number(e.target.value) })}
                                className="w-full h-1.5 rounded-full appearance-none cursor-pointer bg-gray-200 dark:bg-[#2A2A2E] accent-blue-600"
                                aria-label={`${label} weight`}
                            />
                            <p className="text-[10px] text-gray-400 mt-0.5">{description}</p>
                        </div>
                    );
                })}
            </div>
            {/* Visual bar showing proportions */}
            {total > 0 && (
                <div className="flex h-2 rounded-full overflow-hidden mt-3">
                    <div className="bg-blue-500 transition-all" style={{ width: `${(weights.momentum / total) * 100}%` }} />
                    <div className="bg-emerald-500 transition-all" style={{ width: `${(weights.mean_reversion / total) * 100}%` }} />
                    <div className="bg-amber-500 transition-all" style={{ width: `${(weights.volatility / total) * 100}%` }} />
                </div>
            )}
        </div>
    );
}
