import React, { useState, useEffect } from 'react';
import { RefreshCw, Search, ChevronDown, AlertTriangle, CheckCircle, XCircle, ArrowUpDown, Download } from 'lucide-react';

const API = 'http://127.0.0.1:8000';

const SEVERITY_STYLES = {
    CRITICAL: 'bg-rose-100 text-rose-700 border-rose-200',
    WARNING: 'bg-orange-100 text-orange-700 border-orange-200',
    INFO: 'bg-slate-100 text-slate-600 border-slate-200',
};

const STATUS_STYLES = {
    MISSING_IN_GSTR1: { bg: 'bg-rose-50', text: 'text-rose-700', icon: XCircle },
    MISSING_IN_GSTR2B: { bg: 'bg-rose-50', text: 'text-rose-700', icon: XCircle },
    VALUE_MISMATCH: { bg: 'bg-orange-50', text: 'text-orange-700', icon: AlertTriangle },
    TAX_MISMATCH: { bg: 'bg-amber-50', text: 'text-amber-700', icon: AlertTriangle },
    FULLY_RECONCILED: { bg: 'bg-emerald-50', text: 'text-emerald-700', icon: CheckCircle },
};

export default function ReconciliationPage() {
    const [data, setData] = useState(null);
    const [loading, setLoading] = useState(true);
    const [filter, setFilter] = useState('ALL');
    const [searchTerm, setSearchTerm] = useState('');
    const [explanation, setExplanation] = useState(null);
    const [explainLoading, setExplainLoading] = useState(false);
    const [sortField, setSortField] = useState('severity');
    const [sortDir, setSortDir] = useState('asc');

    useEffect(() => {
        fetch(`${API}/api/v1/reconcile/mismatches`)
            .then(r => r.json())
            .then(d => { setData(d); setLoading(false); })
            .catch(() => setLoading(false));
    }, []);

    const handleExplain = (invoiceId) => {
        setExplainLoading(true);
        setExplanation(null);
        fetch(`${API}/api/v1/explain/mismatch/${invoiceId}`)
            .then(r => r.json())
            .then(d => { setExplanation(d); setExplainLoading(false); })
            .catch(() => setExplainLoading(false));
    };

    if (loading) {
        return (
            <div className="flex items-center justify-center h-96">
                <RefreshCw className="animate-spin text-indigo-600 mr-3" size={24} />
                <span className="text-slate-600 font-medium">Running reconciliation engine...</span>
            </div>
        );
    }

    const summary = data?.summary || {};
    const mismatches = data?.mismatches || [];

    // Filter and search
    let filtered = mismatches;
    if (filter !== 'ALL') {
        filtered = filtered.filter(m => m.status === filter);
    }
    if (searchTerm) {
        const term = searchTerm.toLowerCase();
        filtered = filtered.filter(m =>
            m.invoice_id.toLowerCase().includes(term) ||
            m.supplier_gstin.toLowerCase().includes(term) ||
            m.receiver_gstin.toLowerCase().includes(term)
        );
    }

    // Sort
    const severityOrder = { CRITICAL: 0, WARNING: 1, INFO: 2 };
    filtered.sort((a, b) => {
        let cmp = 0;
        if (sortField === 'severity') {
            cmp = (severityOrder[a.severity] || 3) - (severityOrder[b.severity] || 3);
        } else if (sortField === 'value_difference') {
            cmp = b.value_difference - a.value_difference;
        } else if (sortField === 'invoice_id') {
            cmp = a.invoice_id.localeCompare(b.invoice_id);
        }
        return sortDir === 'asc' ? cmp : -cmp;
    });

    const toggleSort = (field) => {
        if (sortField === field) {
            setSortDir(prev => prev === 'asc' ? 'desc' : 'asc');
        } else {
            setSortField(field);
            setSortDir('asc');
        }
    };

    const handleExportCSV = async () => {
        try {
            const res = await fetch(`${API}/api/v1/export/mismatches`);
            const json = await res.json();
            const rows = json.data || [];
            if (rows.length === 0) return;
            const headers = Object.keys(rows[0]);
            const csv = [headers.join(','), ...rows.map(r => headers.map(h => `"${r[h] ?? ''}"`).join(','))].join('\n');
            const blob = new Blob([csv], { type: 'text/csv' });
            const url = URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url; a.download = `mismatches-${new Date().toISOString().slice(0, 10)}.csv`;
            a.click(); URL.revokeObjectURL(url);
        } catch { /* fail silently */ }
    };

    return (
        <div className="space-y-6">
            {/* Summary Cards */}
            <div className="flex justify-between items-center">
                <div className="grid grid-cols-2 md:grid-cols-5 gap-4 flex-1">
                <div className="bg-white rounded-xl p-4 border border-slate-200 shadow-sm text-center">
                    <p className="text-xs text-slate-500 font-medium uppercase tracking-wide">Total Invoices</p>
                    <p className="text-2xl font-bold text-slate-900 mt-1">{summary.total_invoices || 0}</p>
                </div>
                <div className="bg-emerald-50 rounded-xl p-4 border border-emerald-200 shadow-sm text-center">
                    <p className="text-xs text-emerald-600 font-medium uppercase tracking-wide">Reconciled</p>
                    <p className="text-2xl font-bold text-emerald-700 mt-1">{summary.fully_reconciled || 0}</p>
                    <p className="text-xs text-emerald-500 mt-1">{summary.reconciliation_rate || 0}%</p>
                </div>
                <div className="bg-rose-50 rounded-xl p-4 border border-rose-200 shadow-sm text-center">
                    <p className="text-xs text-rose-600 font-medium uppercase tracking-wide">Missing GSTR-1</p>
                    <p className="text-2xl font-bold text-rose-700 mt-1">{summary.missing_in_gstr1 || 0}</p>
                </div>
                <div className="bg-orange-50 rounded-xl p-4 border border-orange-200 shadow-sm text-center">
                    <p className="text-xs text-orange-600 font-medium uppercase tracking-wide">Value Mismatch</p>
                    <p className="text-2xl font-bold text-orange-700 mt-1">{summary.value_mismatch || 0}</p>
                </div>
                <div className="bg-amber-50 rounded-xl p-4 border border-amber-200 shadow-sm text-center">
                    <p className="text-xs text-amber-600 font-medium uppercase tracking-wide">ITC Overclaim</p>
                    <p className="text-2xl font-bold text-amber-700 mt-1">{summary.itc_overclaimed_count || 0}</p>
                </div>
                </div>
                <button onClick={handleExportCSV} className="flex items-center gap-2 px-4 py-2 bg-indigo-600 text-white rounded-lg text-sm font-semibold hover:bg-indigo-700 transition-colors shadow-md self-start mt-2 ml-4 flex-shrink-0">
                    <Download size={16} /> Export CSV
                </button>
            </div>

            {/* Filters + Search */}
            <div className="flex flex-wrap items-center gap-3">
                <div className="relative flex-1 max-w-sm">
                    <Search size={16} className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400" />
                    <input
                        type="text" placeholder="Search invoices or GSTINs..."
                        value={searchTerm} onChange={e => setSearchTerm(e.target.value)}
                        className="w-full pl-9 pr-4 py-2 bg-white border border-slate-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500/20 focus:border-indigo-300"
                    />
                </div>
                <div className="flex gap-1.5">
                    {['ALL', 'VALUE_MISMATCH', 'MISSING_IN_GSTR1', 'MISSING_IN_GSTR2B', 'TAX_MISMATCH'].map(f => (
                        <button key={f} onClick={() => setFilter(f)}
                            className={`px-3 py-1.5 rounded-lg text-xs font-semibold border transition-colors ${filter === f ? 'bg-indigo-600 text-white border-indigo-600' : 'bg-white text-slate-600 border-slate-200 hover:bg-slate-50'}`}>
                            {f === 'ALL' ? 'All' : f.replace(/_/g, ' ')}
                        </button>
                    ))}
                </div>
            </div>

            {/* Mismatch Table */}
            <div className="bg-white rounded-xl border border-slate-200 shadow-sm overflow-hidden">
                <div className="overflow-x-auto">
                    <table className="min-w-full divide-y divide-slate-200">
                        <thead className="bg-slate-50">
                            <tr>
                                <th onClick={() => toggleSort('invoice_id')} className="px-4 py-3 text-left text-xs font-bold text-slate-500 uppercase tracking-wider cursor-pointer hover:text-slate-700">
                                    <span className="flex items-center gap-1">Invoice ID <ArrowUpDown size={12} /></span>
                                </th>
                                <th className="px-4 py-3 text-left text-xs font-bold text-slate-500 uppercase tracking-wider">Supplier</th>
                                <th className="px-4 py-3 text-left text-xs font-bold text-slate-500 uppercase tracking-wider">Receiver</th>
                                <th className="px-4 py-3 text-left text-xs font-bold text-slate-500 uppercase tracking-wider">Status</th>
                                <th onClick={() => toggleSort('severity')} className="px-4 py-3 text-left text-xs font-bold text-slate-500 uppercase tracking-wider cursor-pointer hover:text-slate-700">
                                    <span className="flex items-center gap-1">Severity <ArrowUpDown size={12} /></span>
                                </th>
                                <th className="px-4 py-3 text-right text-xs font-bold text-slate-500 uppercase tracking-wider">GSTR-1 Value</th>
                                <th className="px-4 py-3 text-right text-xs font-bold text-slate-500 uppercase tracking-wider">GSTR-2B Value</th>
                                <th onClick={() => toggleSort('value_difference')} className="px-4 py-3 text-right text-xs font-bold text-slate-500 uppercase tracking-wider cursor-pointer hover:text-slate-700">
                                    <span className="flex items-center gap-1 justify-end">Difference <ArrowUpDown size={12} /></span>
                                </th>
                                <th className="px-4 py-3 text-center text-xs font-bold text-slate-500 uppercase tracking-wider">Explain</th>
                            </tr>
                        </thead>
                        <tbody className="bg-white divide-y divide-slate-100">
                            {filtered.length === 0 ? (
                                <tr><td colSpan={9} className="text-center py-12 text-slate-400 text-sm">No mismatches found — all invoices are fully reconciled ✅</td></tr>
                            ) : (
                                filtered.map((row, i) => {
                                    const statusStyle = STATUS_STYLES[row.status] || STATUS_STYLES.VALUE_MISMATCH;
                                    const StatusIcon = statusStyle.icon;
                                    return (
                                        <tr key={i} className="hover:bg-slate-50/50 transition-colors">
                                            <td className="px-4 py-3 text-sm font-mono font-medium text-slate-900">{row.invoice_id}</td>
                                            <td className="px-4 py-3 text-sm font-mono text-slate-600">{row.supplier_gstin?.slice(0, 12)}</td>
                                            <td className="px-4 py-3 text-sm font-mono text-slate-600">{row.receiver_gstin?.slice(0, 12)}</td>
                                            <td className="px-4 py-3">
                                                <span className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-semibold ${statusStyle.bg} ${statusStyle.text}`}>
                                                    <StatusIcon size={12} /> {row.status?.replace(/_/g, ' ')}
                                                </span>
                                            </td>
                                            <td className="px-4 py-3">
                                                <span className={`inline-flex px-2 py-0.5 rounded border text-xs font-bold uppercase ${SEVERITY_STYLES[row.severity] || SEVERITY_STYLES.INFO}`}>
                                                    {row.severity}
                                                </span>
                                            </td>
                                            <td className="px-4 py-3 text-right text-sm font-medium text-slate-900">₹{row.gstr1_value?.toLocaleString('en-IN')}</td>
                                            <td className="px-4 py-3 text-right text-sm font-medium text-slate-900">₹{row.gstr2b_value?.toLocaleString('en-IN')}</td>
                                            <td className="px-4 py-3 text-right text-sm font-bold text-rose-600">₹{row.value_difference?.toLocaleString('en-IN')}</td>
                                            <td className="px-4 py-3 text-center">
                                                <button onClick={() => handleExplain(row.invoice_id)}
                                                    className="text-indigo-600 hover:text-indigo-800 text-xs font-semibold hover:underline">
                                                    Explain
                                                </button>
                                            </td>
                                        </tr>
                                    );
                                })
                            )}
                        </tbody>
                    </table>
                </div>
            </div>

            {/* Explanation Panel */}
            {(explanation || explainLoading) && (
                <div className="bg-gradient-to-br from-indigo-50 to-white rounded-xl border border-indigo-200 shadow-sm p-6">
                    <div className="flex justify-between items-start mb-3">
                        <h3 className="font-semibold text-indigo-900 flex items-center gap-2">✨ AI Explanation</h3>
                        <button onClick={() => setExplanation(null)} className="text-slate-400 hover:text-slate-600 text-sm">✕</button>
                    </div>
                    {explainLoading ? (
                        <div className="flex items-center gap-2">
                            <RefreshCw size={16} className="animate-spin text-indigo-600" />
                            <span className="text-sm text-slate-500">Analyzing mismatch...</span>
                        </div>
                    ) : (
                        <div>
                            <p className="text-sm text-slate-700 leading-relaxed mb-3">{explanation?.detailed_explanation || explanation?.summary}</p>
                            {explanation?.recommended_actions && (
                                <div className="mt-3">
                                    <p className="text-xs font-semibold text-slate-500 uppercase tracking-wider mb-2">Recommended Actions</p>
                                    <ul className="space-y-1">
                                        {explanation.recommended_actions.map((action, i) => (
                                            <li key={i} className="text-xs text-slate-600 flex items-start gap-2">
                                                <span className="text-indigo-500 mt-0.5">•</span> {action}
                                            </li>
                                        ))}
                                    </ul>
                                </div>
                            )}
                        </div>
                    )}
                </div>
            )}
        </div>
    );
}
