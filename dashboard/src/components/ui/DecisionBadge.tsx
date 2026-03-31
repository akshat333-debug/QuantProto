import { Shield, AlertTriangle } from "lucide-react";

export function DecisionBadge({ action, passed }: { action: string; passed: boolean }) {
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
