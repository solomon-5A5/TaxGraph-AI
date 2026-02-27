import React, { useState, useEffect } from 'react';
import { RefreshCw, AlertTriangle, ArrowRight, Repeat, FileWarning, Building, Download } from 'lucide-react';

const API = 'http://127.0.0.1:8000';

const TAB_CONFIG = [
    { key: 'circular_trades', label: 'Circular Trading', icon: Repeat, color: 'rose' },
    { key: 'shell_companies', label: 'Shell Companies', icon: Building, color: 'purple' },
    { key: 'reciprocal_trades', label: 'Reciprocal Trading', icon: ArrowRight, color: 'orange' },
    { key: 'fake_invoices', label: 'Fake Invoices', icon: FileWarning, color: 'amber' },
];

export default function FraudPage() {
    const [data, setData] = useState(null);
    const [loading, setLoading] = useState(true);
    const [activeTab, setActiveTab] = useState('circular_trades');

    useEffect(() => {
        fetch(`${API}/api/v1/fraud/patterns`)
            .then(r => r.json())
            .then(d => { setData(d); setLoading(false); })
            .catch(() => setLoading(false));
    }, []);

    if (loading) {
        return (
            <div className="flex items-center justify-center h-96">
                <RefreshCw className="animate-spin text-indigo-600 mr-3" size={24} />
                <span className="text-slate-600 font-medium">Running fraud detection algorithms...</span>
            </div>
        );
    }

    const summary = data?.summary || {};

    const handleExportFraud = async () => {
        try {
            const res = await fetch(`${API}/api/v1/export/fraud-report`);
            const json = await res.json();
            const report = json.data || {};
            const rows = [];
            (report.circular_trades || []).forEach(ct => rows.push({ type: 'Circular', chain: ct.chain?.join(' → '), value: ct.total_value }));
            (report.shell_companies || []).forEach(sc => rows.push({ type: 'Shell', gstin: sc.gstin, reason: sc.reason, volume: sc.volume }));
            (report.reciprocal_trades || []).forEach(rt => rows.push({ type: 'Reciprocal', party_a: rt.party_a, party_b: rt.party_b }));
            (report.fake_invoices || []).forEach(fi => rows.push({ type: 'Fake Invoice', supplier: fi.supplier_gstin, amount: fi.amount }));
            if (rows.length === 0) return;
            const headers = ['type', 'chain', 'gstin', 'reason', 'volume', 'value', 'party_a', 'party_b', 'supplier', 'amount'];
            const csv = [headers.join(','), ...rows.map(r => headers.map(h => `"${r[h] ?? ''}"`).join(','))].join('\n');
            const blob = new Blob([csv], { type: 'text/csv' });
            const url = URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url; a.download = `fraud-report-${new Date().toISOString().slice(0, 10)}.csv`;
            a.click(); URL.revokeObjectURL(url);
        } catch { /* fail silently */ }
    };

    return (
        <div className="space-y-6">
            {/* Header with export */}
            <div className="flex justify-between items-center">
                <div>
                    <h2 className="text-xl font-bold text-slate-900">Fraud Detection Engine</h2>
                    <p className="text-sm text-slate-500 mt-1">4-pattern detection: Circular, Shell, Reciprocal, Fake Invoices</p>
                </div>
                <button onClick={handleExportFraud}
                    className="flex items-center gap-2 px-4 py-2 bg-indigo-600 text-white rounded-lg text-sm font-semibold hover:bg-indigo-700 transition-colors shadow-md">
                    <Download size={16} /> Export Report
                </button>
            </div>

            {/* Summary Cards */}
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                {TAB_CONFIG.map(tab => (
                    <button key={tab.key} onClick={() => setActiveTab(tab.key)}
                        className={`rounded-xl p-4 border shadow-sm text-left transition-all ${activeTab === tab.key ? `bg-${tab.color}-50 border-${tab.color}-300 ring-2 ring-${tab.color}-200` : 'bg-white border-slate-200 hover:shadow-md'}`}>
                        <div className="flex items-center gap-2 mb-2">
                            <tab.icon size={18} className={`text-${tab.color}-500`} />
                            <p className="text-xs text-slate-500 font-semibold uppercase tracking-wider">{tab.label}</p>
                        </div>
                        <p className="text-2xl font-bold text-slate-900">{summary[`${tab.key.replace('_trades', '').replace('_invoices', '').replace('_companies', '')}_count`] ?? data?.[tab.key]?.length ?? 0}</p>
                    </button>
                ))}
            </div>

            {/* Active Tab Content */}
            <div className="bg-white rounded-xl border border-slate-200 shadow-sm overflow-hidden">
                <div className="p-5 border-b border-slate-100">
                    <h3 className="font-semibold text-slate-900 text-lg">
                        {TAB_CONFIG.find(t => t.key === activeTab)?.label} Detection Results
                    </h3>
                    <p className="text-xs text-slate-500 mt-1">
                        {activeTab === 'circular_trades' && 'Detected via NetworkX simple_cycles() — DFS graph traversal'}
                        {activeTab === 'shell_companies' && 'Detected via PageRank anomaly — low importance, high volume'}
                        {activeTab === 'reciprocal_trades' && 'Detected via bidirectional edge analysis — A↔B invoice pairs'}
                        {activeTab === 'fake_invoices' && 'Detected via round-number pattern analysis on invoice values'}
                    </p>
                </div>

                {/* Circular Trades */}
                {activeTab === 'circular_trades' && (
                    <div className="p-5 space-y-4">
                        {(data?.circular_trades || []).length === 0 ? (
                            <p className="text-sm text-slate-400 text-center py-8">No circular trading patterns detected</p>
                        ) : (
                            (data?.circular_trades || []).map((ct, i) => (
                                <div key={i} className="bg-rose-50/50 rounded-xl border border-rose-200 p-5">
                                    <div className="flex justify-between items-start mb-3">
                                        <div>
                                            <span className="inline-flex px-2 py-0.5 bg-rose-100 text-rose-700 text-xs font-bold rounded border border-rose-200 uppercase">
                                                CRITICAL — Ring #{i + 1}
                                            </span>
                                            <p className="text-sm text-slate-600 mt-2">Chain length: {ct.chain_length} entities</p>
                                        </div>
                                        <p className="text-lg font-bold text-rose-700">{ct.formatted_value}</p>
                                    </div>
                                    {/* Chain visualization */}
                                    <div className="flex items-center flex-wrap gap-2 mt-3">
                                        {ct.chain.map((gstin, j) => (
                                            <React.Fragment key={j}>
                                                <span className="bg-white px-3 py-1.5 rounded-lg border border-rose-200 text-xs font-mono font-semibold text-slate-800 shadow-sm">
                                                    {gstin.slice(0, 12)}...
                                                </span>
                                                {j < ct.chain.length - 1 && (
                                                    <ArrowRight size={16} className="text-rose-400" />
                                                )}
                                            </React.Fragment>
                                        ))}
                                        <ArrowRight size={16} className="text-rose-400" />
                                        <span className="bg-rose-100 px-3 py-1.5 rounded-lg border border-rose-300 text-xs font-mono font-bold text-rose-700">
                                            ↩ CYCLE
                                        </span>
                                    </div>
                                    {/* Edge details */}
                                    <div className="mt-4 space-y-1">
                                        {ct.edges.map((edge, k) => (
                                            <div key={k} className="flex items-center gap-2 text-xs text-slate-500">
                                                <span className="font-mono">{edge.from?.slice(0, 10)}</span>
                                                <ArrowRight size={12} className="text-rose-300" />
                                                <span className="font-mono">{edge.to?.slice(0, 10)}</span>
                                                <span className="text-slate-400">•</span>
                                                <span className="font-medium text-slate-700">{edge.invoice_id}</span>
                                                <span className="text-slate-400">•</span>
                                                <span className="font-semibold text-rose-600">₹{edge.value?.toLocaleString('en-IN')}</span>
                                            </div>
                                        ))}
                                    </div>
                                </div>
                            ))
                        )}
                    </div>
                )}

                {/* Shell Companies */}
                {activeTab === 'shell_companies' && (
                    <div className="p-5">
                        {(data?.shell_companies || []).length === 0 ? (
                            <p className="text-sm text-slate-400 text-center py-8">No shell companies detected with current thresholds</p>
                        ) : (
                            <div className="space-y-3">
                                {(data?.shell_companies || []).map((sc, i) => (
                                    <div key={i} className="bg-purple-50/50 rounded-lg border border-purple-200 p-4 flex justify-between items-center">
                                        <div>
                                            <p className="font-mono text-sm text-slate-900 font-semibold">{sc.gstin}</p>
                                            <p className="text-xs text-slate-500 mt-1">{sc.reason}</p>
                                            <p className="text-xs text-slate-400 mt-1">PageRank: {sc.pagerank} · Invoices: {sc.invoice_count}</p>
                                        </div>
                                        <div className="text-right">
                                            <p className="text-lg font-bold text-purple-700">{sc.formatted_volume}</p>
                                            <span className="inline-flex px-2 py-0.5 bg-purple-100 text-purple-700 text-xs font-bold rounded border border-purple-200 uppercase">
                                                {sc.severity}
                                            </span>
                                        </div>
                                    </div>
                                ))}
                            </div>
                        )}
                    </div>
                )}

                {/* Reciprocal Trades */}
                {activeTab === 'reciprocal_trades' && (
                    <div className="p-5">
                        {(data?.reciprocal_trades || []).length === 0 ? (
                            <p className="text-sm text-slate-400 text-center py-8">No reciprocal trading patterns detected</p>
                        ) : (
                            <div className="overflow-x-auto">
                                <table className="min-w-full divide-y divide-slate-200">
                                    <thead className="bg-slate-50">
                                        <tr>
                                            <th className="px-4 py-3 text-left text-xs font-bold text-slate-500 uppercase">Party A</th>
                                            <th className="px-4 py-3 text-center text-xs font-bold text-slate-500 uppercase">Direction</th>
                                            <th className="px-4 py-3 text-left text-xs font-bold text-slate-500 uppercase">Party B</th>
                                            <th className="px-4 py-3 text-right text-xs font-bold text-slate-500 uppercase">A → B Value</th>
                                            <th className="px-4 py-3 text-right text-xs font-bold text-slate-500 uppercase">B → A Value</th>
                                        </tr>
                                    </thead>
                                    <tbody className="divide-y divide-slate-100">
                                        {(data?.reciprocal_trades || []).map((rt, i) => (
                                            <tr key={i} className="hover:bg-orange-50/50 transition-colors">
                                                <td className="px-4 py-3 font-mono text-sm text-slate-900">{rt.party_a?.slice(0, 15)}</td>
                                                <td className="px-4 py-3 text-center text-orange-500 font-bold">↔</td>
                                                <td className="px-4 py-3 font-mono text-sm text-slate-900">{rt.party_b?.slice(0, 15)}</td>
                                                <td className="px-4 py-3 text-right text-sm font-semibold text-slate-900">{rt.a_to_b_formatted}</td>
                                                <td className="px-4 py-3 text-right text-sm font-semibold text-slate-900">{rt.b_to_a_formatted}</td>
                                            </tr>
                                        ))}
                                    </tbody>
                                </table>
                            </div>
                        )}
                    </div>
                )}

                {/* Fake Invoices */}
                {activeTab === 'fake_invoices' && (
                    <div className="p-5">
                        {(data?.fake_invoices || []).length === 0 ? (
                            <p className="text-sm text-slate-400 text-center py-8">No fake invoice patterns detected with current thresholds</p>
                        ) : (
                            <div className="space-y-3">
                                {(data?.fake_invoices || []).map((fi, i) => (
                                    <div key={i} className="bg-amber-50/50 rounded-lg border border-amber-200 p-4">
                                        <div className="flex justify-between items-center">
                                            <div>
                                                <p className="text-sm font-semibold text-slate-900">{fi.reason}</p>
                                                <p className="text-xs text-slate-500 mt-1">
                                                    <span className="font-mono">{fi.supplier_gstin?.slice(0, 12)}</span> → <span className="font-mono">{fi.receiver_gstin?.slice(0, 12)}</span>
                                                </p>
                                            </div>
                                            <p className="text-lg font-bold text-amber-700">{fi.formatted_amount}</p>
                                        </div>
                                    </div>
                                ))}
                            </div>
                        )}
                    </div>
                )}
            </div>
        </div>
    );
}
