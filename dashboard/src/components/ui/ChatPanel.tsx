"use client";

import { useState, useRef, useEffect } from "react";
import { MessageCircle, Send, X, Sparkles, Bot, User } from "lucide-react";
import { sendAIChat } from "@/lib/api";
import type { AnalysisData } from "@/lib/types";

type Message = {
    role: "user" | "assistant";
    content: string;
};

export function ChatPanel({ data }: { data: AnalysisData | null }) {
    const [isOpen, setIsOpen] = useState(false);
    const [messages, setMessages] = useState<Message[]>([]);
    const [input, setInput] = useState("");
    const [loading, setLoading] = useState(false);
    const messagesEndRef = useRef<HTMLDivElement>(null);

    useEffect(() => {
        messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
    }, [messages]);

    const handleSend = async () => {
        const q = input.trim();
        if (!q || loading) return;
        setInput("");
        setMessages((prev) => [...prev, { role: "user", content: q }]);
        setLoading(true);
        try {
            const res = await sendAIChat(q, data as unknown as Record<string, unknown>);
            setMessages((prev) => [...prev, { role: "assistant", content: res.response }]);
        } catch {
            setMessages((prev) => [...prev, { role: "assistant", content: "*Failed to get AI response. Is the API running?*" }]);
        } finally {
            setLoading(false);
        }
    };

    if (!isOpen) {
        return (
            <button
                onClick={() => setIsOpen(true)}
                className="fixed bottom-6 right-6 z-50 w-14 h-14 rounded-full bg-gradient-to-br from-blue-600 to-purple-600 text-white shadow-2xl hover:scale-105 transition-transform flex items-center justify-center"
                aria-label="Open AI Chat"
            >
                <MessageCircle className="w-6 h-6" />
            </button>
        );
    }

    return (
        <div className="fixed bottom-6 right-6 z-50 w-[380px] max-h-[520px] bg-white dark:bg-[#0F0F12] rounded-2xl border border-gray-200 dark:border-[#1F1F23] shadow-2xl flex flex-col overflow-hidden">
            {/* Header */}
            <div className="flex items-center justify-between px-4 py-3 border-b border-gray-200 dark:border-[#1F1F23] bg-gradient-to-r from-blue-600/10 to-purple-600/10">
                <div className="flex items-center gap-2">
                    <Sparkles className="w-4 h-4 text-purple-500" />
                    <span className="text-sm font-semibold">QuantProto AI</span>
                </div>
                <button onClick={() => setIsOpen(false)} className="p-1 rounded-md hover:bg-gray-100 dark:hover:bg-[#1F1F23] transition-colors" aria-label="Close chat">
                    <X className="w-4 h-4" />
                </button>
            </div>

            {/* Messages */}
            <div className="flex-1 overflow-y-auto p-4 space-y-3 min-h-[200px] max-h-[360px]">
                {messages.length === 0 && (
                    <div className="text-center py-8">
                        <Bot className="w-10 h-10 mx-auto mb-3 text-purple-500/50" />
                        <p className="text-sm text-gray-500 dark:text-gray-400">Ask anything about your analysis</p>
                        <div className="mt-3 space-y-1">
                            {["What are the main risk concerns?", "Explain the Sharpe ratio", "Should I rebalance?"].map((q) => (
                                <button
                                    key={q}
                                    onClick={() => { setInput(q); }}
                                    className="block w-full text-left text-xs px-3 py-1.5 rounded-lg bg-gray-50 dark:bg-[#1A1A1E] hover:bg-gray-100 dark:hover:bg-[#252528] text-gray-600 dark:text-gray-400 transition-colors"
                                >
                                    {q}
                                </button>
                            ))}
                        </div>
                    </div>
                )}

                {messages.map((m, i) => (
                    <div key={i} className={`flex gap-2 ${m.role === "user" ? "justify-end" : "justify-start"}`}>
                        {m.role === "assistant" && <Bot className="w-5 h-5 text-purple-500 flex-shrink-0 mt-1" />}
                        <div className={`max-w-[80%] rounded-xl px-3 py-2 text-sm ${m.role === "user"
                            ? "bg-blue-600 text-white"
                            : "bg-gray-100 dark:bg-[#1A1A1E] text-gray-800 dark:text-gray-200"
                        }`}>
                            <div className="whitespace-pre-wrap break-words">{m.content}</div>
                        </div>
                        {m.role === "user" && <User className="w-5 h-5 text-blue-500 flex-shrink-0 mt-1" />}
                    </div>
                ))}

                {loading && (
                    <div className="flex gap-2 items-center">
                        <Bot className="w-5 h-5 text-purple-500" />
                        <div className="bg-gray-100 dark:bg-[#1A1A1E] rounded-xl px-3 py-2">
                            <div className="flex gap-1">
                                <span className="w-2 h-2 bg-purple-500/60 rounded-full animate-bounce" style={{ animationDelay: "0ms" }} />
                                <span className="w-2 h-2 bg-purple-500/60 rounded-full animate-bounce" style={{ animationDelay: "150ms" }} />
                                <span className="w-2 h-2 bg-purple-500/60 rounded-full animate-bounce" style={{ animationDelay: "300ms" }} />
                            </div>
                        </div>
                    </div>
                )}

                <div ref={messagesEndRef} />
            </div>

            {/* Input */}
            <div className="px-3 py-2 border-t border-gray-200 dark:border-[#1F1F23]">
                <div className="flex gap-2">
                    <input
                        value={input}
                        onChange={(e) => setInput(e.target.value)}
                        onKeyDown={(e) => { if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); handleSend(); } }}
                        placeholder="Ask about your portfolio..."
                        className="flex-1 h-9 px-3 rounded-lg bg-gray-50 dark:bg-[#1A1A1E] border border-gray-200 dark:border-[#2A2A2E] text-sm focus:outline-none focus:ring-2 focus:ring-purple-500/50"
                    />
                    <button
                        onClick={handleSend}
                        disabled={!input.trim() || loading}
                        className="h-9 w-9 rounded-lg bg-purple-600 hover:bg-purple-500 text-white flex items-center justify-center transition-colors disabled:opacity-50"
                        aria-label="Send message"
                    >
                        <Send className="w-4 h-4" />
                    </button>
                </div>
            </div>
        </div>
    );
}
