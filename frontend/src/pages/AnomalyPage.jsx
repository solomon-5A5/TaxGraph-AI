import React, { useState, useEffect } from 'react';
import { RefreshCw, Activity, AlertTriangle, TrendingUp, Download, BarChart3, Zap, Building } from 'lucide-react';
import {
    BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Cell,
    ScatterChart, Scatter, ZAxis, Legend
} from 'recharts';
import { API } from '../config';

const SEVERITY_STYLE = {
    HIGH: 'bg-rose-100 text-rose-700 border-rose-200',
    MEDIUM: 'bg-amber-100 text-amber-700 border-amber-200',
    LOW: 'bg-slate-100 text-slate-600 border-slate-200',
};

const TAB_CONFIG = [
    { key: 'invoices', label: 'Invoice Outliers', icon: BarChart3, color: 'indigo' },
    { key: 'vendors', label: 'Vendor Anomalies', icon: Building, color: 'purple' },
    { key: 'itc', label: 'ITC Ratio Anomalies', icon: TrendingUp, color: 'amber' },
];

export default function AnomalyPage() {
    const [data, setData] = useState(null);
    const [loading, setLoading] = useState(true);
    const [activeTab, setActiveTab] = useState('invoices');

    useEffect(() => {
        fetch(`${API}/api/v1/anomalies`)
            .then(r => r.json())
            .then(d => { setData(d); setLoading(false); })
            .catch(() => setLoading(false));
    }, []);

    const handleExport = () => {
        if (!data) return;
        const allAnomalies = [
            ...(data.invoice_anomalies || []).map(a => ({ type: 'Invoice', ...a })),
            ...(data.vendor_anomalies || []).map(a => ({ type: 'Vendor', ...a })),
            ...(data.itc_anomalies || []).map(a => ({ type: 'ITC', ...a })),
        ];
        if (allAnomalies.length === 0) return;
        const headers = Object.keys(allAnomalies[0]);
        const csv = [headers.join(','), ...allAnomalies.map(r => headers.map(h => `"${r[h] ?? ''}"`).join(','))].join('\n');
        const blob = new Blob([csv], { type: 'text/csv' });
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url; a.download = `anomaly-report-${new Date().toISOString().slice(0, 10)}.csv`;
        a.click(); URL.revokeObjectURL(url);
    };

    if (loading) {
        return (
            <div className="flex items-center justify-center h-96">
                <RefreshCw className="animate-spin text-indigo-600 mr-3" size={24} />
                <span className="text-slate-600 font-medium">Running statistical anomaly detection (Z-score & IQR)...</span>
            </div>
        );
    }

    const summary = data?.summary || {};
    const invoiceAnomalies = data?.invoice_anomalies || [];
    const vendorAnomalies = data?.vendor_anomalies || [];
    const itcAnomalies = data?.itc_anomalies || [];

    // Chart data — invoice value distribution for outliers
    const invoiceChartData = invoiceAnomalies.slice(0, 15).map(a => ({
        name: a.invoice_id?.slice(0, 8) || 'N/A',
        value: a.invoice_value || 0,
        z_score: Math.abs(a.z_score || 0).toFixed(2),
    }));

    const confidenceColor = (c) => {
        if (c >= 0.8) return 'text-rose-600';
        if (c >= 0.5) return 'text-amber-600';
        return 'text-slate-600';
    };

    return (
        <div className="space-y-6">
            {/* Header */}
            <div className="flex justify-between items-center">
                <div>
                    <h2 className="text-xl font-bold text-slate-900 flex items-center gap-2">
                        <Activity size={22} className="text-purple-600" /> Statistical Anomaly Detection
                    </h2>
                    <p className="text-sm text-slate-500 mt-1">Z-score & IQR-based analysis across invoices, vendors, and ITC ratios</p>
                </div>
                <button onClick={handleExport}
                    className="flex items-center gap-2 px-4 py-2 bg-indigo-600 text-white rounded-lg text-sm font-semibold hover:bg-indigo-700 transition-colors shadow-md">
                    <Download size={16} /> Export Report
                </button>
            </div>

            {/* Summary Cards */}
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                <div className="bg-gradient-to-br from-purple-50 to-indigo-50 rounded-xl p-4 border border-purple-200 shadow-sm text-center">
                    <p className="text-xs text-purple-600 font-semibold uppercase tracking-wide">Total Anomalies</p>
                    <p className="text-3xl font-bold text-purple-700 mt-1">{summary.total_anomalies || 0}</p>
                </div>
                <div className="bg-indigo-50 rounded-xl p-4 border border-indigo-200 shadow-sm text-center">
                    <p className="text-xs text-indigo-600 font-semibold uppercase tracking-wide">Invoice Outliers</p>
                    <p className="text-3xl font-bold text-indigo-700 mt-1">{invoiceAnomalies.length}</p>
                    <p className="text-xs text-indigo-400 mt-1">Z-score &gt; 2.5σ</p>
                </div>
                <div className="bg-purple-50 rounded-xl p-4 border border-purple-200 shadow-sm text-center">
                    <p className="text-xs text-purple-600 font-semibold uppercase tracking-wide">Vendor Anomalies</p>
                    <p className="text-3xl font-bold text-purple-700 mt-1">{vendorAnomalies.length}</p>
                    <p className="text-xs text-purple-400 mt-1">IQR method</p>
                </div>
                <div className="bg-amber-50 rounded-xl p-4 border border-amber-200 shadow-sm text-center">
                    <p className="text-xs text-amber-600 font-semibold uppercase tracking-wide">ITC Ratio Flags</p>
                    <p className="text-3xl font-bold text-amber-700 mt-1">{itcAnomalies.length}</p>
                    <p className="text-xs text-amber-400 mt-1">Ratio analysis</p>
                </div>
            </div>

            {/* Chart — Invoice Outlier Values */}
            {invoiceChartData.length > 0 && (
                <div className="bg-white rounded-xl border border-slate-200 shadow-sm p-5">
                    <h3 className="font-semibold text-slate-900 mb-1">Invoice Value Outliers</h3>
                    <p className="text-xs text-slate-500 mb-4">Top anomalous invoices by value (Z-score &gt; 2.5σ)</p>
                    <ResponsiveContainer width="100%" height={260}>
                        <BarChart data={invoiceChartData} barCategoryGap="15%">
                            <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
                            <XAxis dataKey="name" tick={{ fontSize: 11, fill: '#64748b' }} />
                            <YAxis tick={{ fontSize: 11, fill: '#64748b' }} tickFormatter={v => `₹${(v / 100000).toFixed(0)}L`} />
                            <Tooltip formatter={(val) => [`₹${val.toLocaleString('en-IN')}`, 'Invoice Value']} />
                            <Bar dataKey="value" radius={[6, 6, 0, 0]}>
                                {invoiceChartData.map((entry, i) => (
                                    <Cell key={i} fill={parseFloat(entry.z_score) > 3 ? '#ef4444' : '#6366f1'} />
                                ))}
                            </Bar>
                        </BarChart>
                    </ResponsiveContainer>
                </div>
            )}

            {/* Tab Navigation */}
            <div className="flex gap-2">
                {TAB_CONFIG.map(tab => (
                    <button key={tab.key} onClick={() => setActiveTab(tab.key)}
                        className={`flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-semibold border transition-all ${activeTab === tab.key ? 'bg-indigo-600 text-white border-indigo-600 shadow-md' : 'bg-white text-slate-600 border-slate-200 hover:bg-slate-50'}`}>
                        <tab.icon size={16} /> {tab.label}
                    </button>
                ))}
            </div>

            {/* Tab Content */}
            <div className="bg-white rounded-xl border border-slate-200 shadow-sm overflow-hidden">
                {/* Invoice Outliers */}
                {activeTab === 'invoices' && (
                    <div className="overflow-x-auto">
                        <table className="min-w-full divide-y divide-slate-200">
                            <thead className="bg-slate-50">
                                <tr>
                                    <th className="px-4 py-3 text-left text-xs font-bold text-slate-500 uppercase">Invoice ID</th>
                                    <th className="px-4 py-3 text-left text-xs font-bold text-slate-500 uppercase">Supplier</th>
                                    <th className="px-4 py-3 text-right text-xs font-bold text-slate-500 uppercase">Value</th>
                                    <th className="px-4 py-3 text-right text-xs font-bold text-slate-500 uppercase">Z-Score</th>
                                    <th className="px-4 py-3 text-center text-xs font-bold text-slate-500 uppercase">Confidence</th>
                                    <th className="px-4 py-3 text-center text-xs font-bold text-slate-500 uppercase">Severity</th>
                                </tr>
                            </thead>
                            <tbody className="divide-y divide-slate-100">
                                {invoiceAnomalies.length === 0 ? (
                                    <tr><td colSpan={6} className="text-center py-12 text-slate-400 text-sm">No invoice outliers detected ✅</td></tr>
                                ) : invoiceAnomalies.map((a, i) => (
                                    <tr key={i} className="hover:bg-slate-50 transition-colors">
                                        <td className="px-4 py-3 text-sm font-mono font-medium text-slate-900">{a.invoice_id}</td>
                                        <td className="px-4 py-3 text-sm font-mono text-slate-600">{a.supplier_gstin?.slice(0, 15)}</td>
                                        <td className="px-4 py-3 text-right text-sm font-semibold text-slate-900">₹{a.invoice_value?.toLocaleString('en-IN')}</td>
                                        <td className="px-4 py-3 text-right text-sm font-mono font-bold text-rose-600">{a.z_score?.toFixed(2)}σ</td>
                                        <td className="px-4 py-3 text-center">
                                            <span className={`text-sm font-bold ${confidenceColor(a.confidence)}`}>
                                                {(a.confidence * 100).toFixed(0)}%
                                            </span>
                                        </td>
                                        <td className="px-4 py-3 text-center">
                                            <span className={`inline-flex px-2 py-0.5 rounded border text-xs font-bold uppercase ${SEVERITY_STYLE[a.severity] || SEVERITY_STYLE.LOW}`}>
                                                {a.severity}
                                            </span>
                                        </td>
                                    </tr>
                                ))}
                            </tbody>
                        </table>
                    </div>
                )}

                {/* Vendor Anomalies */}
                {activeTab === 'vendors' && (
                    <div className="p-5 space-y-3">
                        {vendorAnomalies.length === 0 ? (
                            <p className="text-sm text-slate-400 text-center py-8">No vendor anomalies detected ✅</p>
                        ) : vendorAnomalies.map((v, i) => (
                            <div key={i} className="bg-purple-50/50 rounded-lg border border-purple-200 p-4 flex justify-between items-center hover:shadow-md transition-shadow">
                                <div>
                                    <p className="font-mono text-sm text-slate-900 font-semibold">{v.gstin}</p>
                                    <p className="text-xs text-slate-500 mt-1">{v.reason}</p>
                                    <div className="flex items-center gap-3 mt-1 text-xs text-slate-400">
                                        <span>Invoices: {v.invoice_count}</span>
                                        <span>•</span>
                                        <span>Total: ₹{v.total_value?.toLocaleString('en-IN')}</span>
                                    </div>
                                </div>
                                <div className="text-right">
                                    <p className={`text-lg font-bold ${confidenceColor(v.confidence)}`}>{(v.confidence * 100).toFixed(0)}%</p>
                                    <span className={`inline-flex px-2 py-0.5 rounded border text-xs font-bold uppercase ${SEVERITY_STYLE[v.severity] || SEVERITY_STYLE.LOW}`}>
                                        {v.severity}
                                    </span>
                                </div>
                            </div>
                        ))}
                    </div>
                )}

                {/* ITC Ratio Anomalies */}
                {activeTab === 'itc' && (
                    <div className="overflow-x-auto">
                        <table className="min-w-full divide-y divide-slate-200">
                            <thead className="bg-slate-50">
                                <tr>
                                    <th className="px-4 py-3 text-left text-xs font-bold text-slate-500 uppercase">GSTIN</th>
                                    <th className="px-4 py-3 text-right text-xs font-bold text-slate-500 uppercase">ITC Claimed</th>
                                    <th className="px-4 py-3 text-right text-xs font-bold text-slate-500 uppercase">Sales Value</th>
                                    <th className="px-4 py-3 text-right text-xs font-bold text-slate-500 uppercase">ITC/Sales Ratio</th>
                                    <th className="px-4 py-3 text-center text-xs font-bold text-slate-500 uppercase">Confidence</th>
                                    <th className="px-4 py-3 text-center text-xs font-bold text-slate-500 uppercase">Severity</th>
                                </tr>
                            </thead>
                            <tbody className="divide-y divide-slate-100">
                                {itcAnomalies.length === 0 ? (
                                    <tr><td colSpan={6} className="text-center py-12 text-slate-400 text-sm">No ITC ratio anomalies detected ✅</td></tr>
                                ) : itcAnomalies.map((a, i) => (
                                    <tr key={i} className="hover:bg-amber-50/50 transition-colors">
                                        <td className="px-4 py-3 text-sm font-mono font-medium text-slate-900">{a.gstin?.slice(0, 15)}</td>
                                        <td className="px-4 py-3 text-right text-sm font-semibold text-slate-900">₹{a.itc_claimed?.toLocaleString('en-IN')}</td>
                                        <td className="px-4 py-3 text-right text-sm text-slate-600">₹{a.total_sales?.toLocaleString('en-IN')}</td>
                                        <td className="px-4 py-3 text-right text-sm font-bold text-amber-700">{a.itc_ratio?.toFixed(2)}x</td>
                                        <td className="px-4 py-3 text-center">
                                            <span className={`text-sm font-bold ${confidenceColor(a.confidence)}`}>
                                                {(a.confidence * 100).toFixed(0)}%
                                            </span>
                                        </td>
                                        <td className="px-4 py-3 text-center">
                                            <span className={`inline-flex px-2 py-0.5 rounded border text-xs font-bold uppercase ${SEVERITY_STYLE[a.severity] || SEVERITY_STYLE.LOW}`}>
                                                {a.severity}
                                            </span>
                                        </td>
                                    </tr>
                                ))}
                            </tbody>
                        </table>
                    </div>
                )}
            </div>
        </div>
    );
}
