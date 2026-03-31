"use client";

import { useState, useCallback } from "react";
import { Sparkles, RefreshCw, ChevronDown, ChevronUp } from "lucide-react";
import { fetchAISummary } from "@/lib/api";
import type { AnalysisData } from "@/lib/types";

export function AISummary({ data }: { data: AnalysisData }) {
    const [summary, setSummary] = useState<string | null>(null);
    const [loading, setLoading] = useState(false);
    const [expanded, setExpanded] = useState(true);
    const [aiPowered, setAiPowered] = useState(false);

    const generate = useCallback(async () => {
        setLoading(true);
        try {
            const res = await fetchAISummary(data as unknown as Record<string, unknown>);
            setSummary(res.summary);
            setAiPowered(res.ai_powered);
            setExpanded(true);
        } catch {
            setSummary("*Failed to generate summary. Is the API server running?*");
        } finally {
            setLoading(false);
        }
    }, [data]);

    return (
        <div className="bg-gradient-to-r from-purple-600/5 to-blue-600/5 dark:from-purple-600/10 dark:to-blue-600/10 rounded-xl border border-purple-500/20 overflow-hidden">
            <div className="flex items-center justify-between px-5 py-3">
                <div className="flex items-center gap-2">
                    <Sparkles className="w-4 h-4 text-purple-500" />
                    <span className="text-sm font-semibold text-purple-500">AI Executive Summary</span>
                    {aiPowered && <span className="text-[10px] px-1.5 py-0.5 rounded-full bg-purple-500/20 text-purple-400">Gemini</span>}
                    {summary && !aiPowered && <span className="text-[10px] px-1.5 py-0.5 rounded-full bg-gray-500/20 text-gray-400">Mock</span>}
                </div>
                <div className="flex items-center gap-1">
                    {summary && (
                        <button onClick={() => setExpanded(!expanded)} className="p-1 rounded-md hover:bg-purple-500/10 transition-colors" aria-label={expanded ? "Collapse" : "Expand"}>
                            {expanded ? <ChevronUp className="w-4 h-4 text-purple-500" /> : <ChevronDown className="w-4 h-4 text-purple-500" />}
                        </button>
                    )}
                    <button
                        onClick={generate}
                        disabled={loading}
                        className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-semibold bg-purple-600/20 hover:bg-purple-600/30 text-purple-400 transition-colors disabled:opacity-50"
                    >
                        {loading ? <RefreshCw className="w-3 h-3 animate-spin" /> : <Sparkles className="w-3 h-3" />}
                        {summary ? "Regenerate" : "Generate"}
                    </button>
                </div>
            </div>

            {summary && expanded && (
                <div className="px-5 pb-4">
                    <div className="prose prose-sm dark:prose-invert max-w-none text-sm leading-relaxed text-gray-700 dark:text-gray-300 whitespace-pre-wrap">
                        {summary}
                    </div>
                </div>
            )}
        </div>
    );
}
