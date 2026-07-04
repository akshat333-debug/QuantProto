import React from "react";

export function MetricCard({ label, value, sub, icon: Icon, color = "text-gray-100" }: {
    label: string; value: string; sub?: string; icon: React.ElementType; color?: string;
}) {
    // Tint the icon chip from the value colour (e.g. text-emerald-500 → bg-emerald-500/10)
    const chipBg = color.replace("text-", "bg-").replace(/-(\d+)$/, "-500") + "/10";
    return (
        <div className="panel-card bg-white dark:bg-[#0B111C] rounded-2xl p-4 sm:p-5 border border-gray-200 dark:border-[#1B2536] min-w-0">
            <div className="flex items-center justify-between mb-3">
                <span className="text-[10px] sm:text-[11px] font-semibold uppercase tracking-wider text-gray-500 dark:text-gray-400 truncate mr-2">{label}</span>
                <span className={`w-7 h-7 rounded-lg ${chipBg} flex items-center justify-center flex-shrink-0`}>
                    <Icon className={`w-3.5 h-3.5 ${color}`} />
                </span>
            </div>
            <div className={`text-xl sm:text-2xl font-bold font-mono tracking-tight tabular-nums truncate ${color}`}>{value}</div>
            {sub && <div className="text-[10px] sm:text-xs text-gray-500 dark:text-gray-400 mt-1 truncate">{sub}</div>}
        </div>
    );
}
