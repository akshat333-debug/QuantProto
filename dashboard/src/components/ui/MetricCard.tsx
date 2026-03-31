import React from "react";

export function MetricCard({ label, value, sub, icon: Icon, color = "text-gray-100" }: {
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
