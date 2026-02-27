import React, { useState } from 'react';
import { Send, RefreshCw, MessageSquare, Code, Table, AlertTriangle } from 'lucide-react';

const API = 'http://127.0.0.1:8000';

const EXAMPLE_QUERIES = [
    "Show all invoices above 10 lakhs",
    "Find taxpayers with zero cash tax paid",
    "Which vendors have the most invoices?",
    "Show all suspended vendors",
    "What is the total ITC claimed?",
    "Find invoices from fraud-flagged entities",
];

export default function QueryPage() {
    const [question, setQuestion] = useState('');
    const [history, setHistory] = useState([]);
    const [loading, setLoading] = useState(false);

    const handleQuery = async (q) => {
        const queryText = q || question;
        if (!queryText.trim()) return;

        setLoading(true);
        setQuestion('');

        const newEntry = { question: queryText, response: null, loading: true };
        setHistory(prev => [...prev, newEntry]);

        try {
            const res = await fetch(`${API}/api/v1/query`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ question: queryText }),
            });
            const data = await res.json();

            setHistory(prev => {
                const updated = [...prev];
                updated[updated.length - 1] = { question: queryText, response: data, loading: false };
                return updated;
            });
        } catch (err) {
            setHistory(prev => {
                const updated = [...prev];
                updated[updated.length - 1] = {
                    question: queryText,
                    response: { error: true, explanation: 'Failed to connect to the server.' },
                    loading: false,
                };
                return updated;
            });
        }
        setLoading(false);
    };

    return (
        <div className="flex flex-col h-[calc(100vh-8rem)]">
            {/* Header */}
            <div className="mb-4">
                <h2 className="text-xl font-bold text-slate-900 flex items-center gap-2">
                    <MessageSquare size={22} className="text-indigo-600" /> Natural Language Query
                </h2>
                <p className="text-sm text-slate-500 mt-1">Ask questions about GST data in plain English — powered by AI</p>
            </div>

            {/* Chat Area */}
            <div className="flex-1 overflow-y-auto space-y-4 mb-4 pr-2">
                {history.length === 0 ? (
                    <div className="flex flex-col items-center justify-center h-full">
                        <MessageSquare size={48} className="text-slate-200 mb-4" />
                        <p className="text-slate-400 text-sm font-medium mb-6">Ask anything about your GST data</p>
                        <div className="grid grid-cols-1 sm:grid-cols-2 gap-2 max-w-lg w-full">
                            {EXAMPLE_QUERIES.map((eq, i) => (
                                <button key={i} onClick={() => handleQuery(eq)}
                                    className="text-left px-4 py-3 bg-white rounded-xl border border-slate-200 text-sm text-slate-600 hover:bg-indigo-50 hover:border-indigo-200 hover:text-indigo-700 transition-all shadow-sm">
                                    "{eq}"
                                </button>
                            ))}
                        </div>
                    </div>
                ) : (
                    history.map((entry, i) => (
                        <div key={i} className="space-y-3">
                            {/* User message */}
                            <div className="flex justify-end">
                                <div className="bg-indigo-600 text-white px-4 py-2.5 rounded-2xl rounded-br-md max-w-lg text-sm font-medium shadow-md">
                                    {entry.question}
                                </div>
                            </div>

                            {/* AI Response */}
                            <div className="flex justify-start">
                                <div className="bg-white border border-slate-200 rounded-2xl rounded-bl-md max-w-2xl shadow-sm overflow-hidden">
                                    {entry.loading ? (
                                        <div className="p-4 flex items-center gap-2">
                                            <RefreshCw size={16} className="animate-spin text-indigo-600" />
                                            <span className="text-sm text-slate-500">Analyzing your question...</span>
                                        </div>
                                    ) : entry.response?.error ? (
                                        <div className="p-4">
                                            <div className="flex items-center gap-2 text-rose-600 mb-2">
                                                <AlertTriangle size={16} />
                                                <span className="text-sm font-semibold">Error</span>
                                            </div>
                                            <p className="text-sm text-slate-600">{entry.response.explanation}</p>
                                        </div>
                                    ) : (
                                        <div>
                                            {/* Explanation */}
                                            <div className="p-4 border-b border-slate-100">
                                                <p className="text-sm text-slate-700 leading-relaxed">{entry.response.explanation}</p>
                                                {entry.response.row_count !== undefined && (
                                                    <p className="text-xs text-slate-400 mt-2">{entry.response.row_count} rows returned</p>
                                                )}
                                            </div>

                                            {/* Generated Code */}
                                            {entry.response.query && (
                                                <details className="border-b border-slate-100">
                                                    <summary className="px-4 py-2 text-xs font-semibold text-slate-500 cursor-pointer hover:bg-slate-50 flex items-center gap-1">
                                                        <Code size={12} /> View Generated Code
                                                    </summary>
                                                    <pre className="px-4 py-3 text-xs text-slate-600 bg-slate-50 overflow-x-auto font-mono">
                                                        {entry.response.query}
                                                    </pre>
                                                </details>
                                            )}

                                            {/* Results Table */}
                                            {entry.response.results && entry.response.results.length > 0 && (
                                                <div className="overflow-x-auto max-h-64">
                                                    <table className="min-w-full divide-y divide-slate-200 text-xs">
                                                        <thead className="bg-slate-50 sticky top-0">
                                                            <tr>
                                                                {Object.keys(entry.response.results[0]).map(key => (
                                                                    <th key={key} className="px-3 py-2 text-left font-bold text-slate-500 uppercase tracking-wider whitespace-nowrap">
                                                                        {key}
                                                                    </th>
                                                                ))}
                                                            </tr>
                                                        </thead>
                                                        <tbody className="divide-y divide-slate-100">
                                                            {entry.response.results.slice(0, 20).map((row, j) => (
                                                                <tr key={j} className="hover:bg-slate-50">
                                                                    {Object.values(row).map((val, k) => (
                                                                        <td key={k} className="px-3 py-2 text-slate-700 whitespace-nowrap font-mono">
                                                                            {val === null ? '—' : typeof val === 'number' ? val.toLocaleString('en-IN') : String(val).slice(0, 30)}
                                                                        </td>
                                                                    ))}
                                                                </tr>
                                                            ))}
                                                        </tbody>
                                                    </table>
                                                    {entry.response.results.length > 20 && (
                                                        <p className="text-xs text-slate-400 p-2 text-center">Showing 20 of {entry.response.results.length} rows</p>
                                                    )}
                                                </div>
                                            )}
                                        </div>
                                    )}
                                </div>
                            </div>
                        </div>
                    ))
                )}
            </div>

            {/* Input */}
            <div className="border-t border-slate-200 bg-white rounded-xl shadow-lg p-3">
                <form onSubmit={e => { e.preventDefault(); handleQuery(); }} className="flex items-center gap-3">
                    <input
                        type="text" value={question} onChange={e => setQuestion(e.target.value)}
                        placeholder="Ask about your GST data..."
                        disabled={loading}
                        className="flex-1 px-4 py-2.5 bg-slate-50 rounded-lg text-sm border border-slate-200 focus:outline-none focus:ring-2 focus:ring-indigo-500/20 focus:border-indigo-300 disabled:opacity-50"
                    />
                    <button type="submit" disabled={loading || !question.trim()}
                        className="bg-indigo-600 text-white p-2.5 rounded-lg hover:bg-indigo-700 transition-colors disabled:opacity-50 shadow-md">
                        {loading ? <RefreshCw size={18} className="animate-spin" /> : <Send size={18} />}
                    </button>
                </form>
            </div>
        </div>
    );
}
