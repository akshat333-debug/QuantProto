import type { TooltipPayload } from "@/lib/types";

export function ChartTooltip({ active, payload, label }: {
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
