import { AlertTriangle } from "lucide-react";

export function ErrorBanner({ message, onDismiss }: { message: string; onDismiss: () => void }) {
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
