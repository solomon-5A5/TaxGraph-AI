import React, { useState, useEffect } from 'react';
import { RefreshCw, AlertTriangle, Bell, CheckCircle, Filter, Shield } from 'lucide-react';
import { API } from '../config';

const SEVERITY_CONFIG = {
    CRITICAL: { bg: 'bg-rose-50', border: 'border-rose-200', badge: 'bg-rose-100 text-rose-700 border-rose-200', icon: Shield, iconColor: 'text-rose-500' },
    WARNING: { bg: 'bg-orange-50', border: 'border-orange-200', badge: 'bg-orange-100 text-orange-700 border-orange-200', icon: AlertTriangle, iconColor: 'text-orange-500' },
    INFO: { bg: 'bg-slate-50', border: 'border-slate-200', badge: 'bg-slate-100 text-slate-600 border-slate-200', icon: Bell, iconColor: 'text-slate-400' },
};

export default function AlertsPage() {
    const [data, setData] = useState(null);
    const [loading, setLoading] = useState(true);
    const [filter, setFilter] = useState('ALL');

    useEffect(() => {
        fetch(`${API}/api/v1/alerts`)
            .then(r => r.json())
            .then(d => { setData(d); setLoading(false); })
            .catch(() => setLoading(false));
    }, []);

    if (loading) {
        return (
            <div className="flex items-center justify-center h-96">
                <RefreshCw className="animate-spin text-indigo-600 mr-3" size={24} />
                <span className="text-slate-600 font-medium">Loading alerts...</span>
            </div>
        );
    }

    const alerts = data?.alerts || [];

    // Count by severity
    const counts = { ALL: alerts.length, CRITICAL: 0, WARNING: 0, INFO: 0 };
    alerts.forEach(a => { if (counts[a.severity] !== undefined) counts[a.severity]++; });

    // Filter
    const filtered = filter === 'ALL' ? alerts : alerts.filter(a => a.severity === filter);

    return (
        <div className="space-y-6">
            {/* Header */}
            <div className="flex justify-between items-center">
                <div>
                    <h2 className="text-xl font-bold text-slate-900">Alert Center</h2>
                    <p className="text-sm text-slate-500 mt-1">{alerts.length} alerts generated from analysis</p>
                </div>
                <span className="relative flex h-3 w-3">
                    <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-rose-400 opacity-75"></span>
                    <span className="relative inline-flex rounded-full h-3 w-3 bg-rose-600"></span>
                </span>
            </div>

            {/* Filter Bar */}
            <div className="flex gap-2">
                {['ALL', 'CRITICAL', 'WARNING', 'INFO'].map(sev => (
                    <button key={sev} onClick={() => setFilter(sev)}
                        className={`px-4 py-2 rounded-lg text-sm font-semibold border transition-all ${filter === sev ? 'bg-indigo-600 text-white border-indigo-600 shadow-md' : 'bg-white text-slate-600 border-slate-200 hover:bg-slate-50'}`}>
                        {sev === 'ALL' ? `All (${counts.ALL})` : `${sev} (${counts[sev]})`}
                    </button>
                ))}
            </div>

            {/* Alert List */}
            <div className="space-y-3">
                {filtered.length === 0 ? (
                    <div className="bg-emerald-50 rounded-xl border border-emerald-200 p-8 text-center">
                        <CheckCircle size={32} className="text-emerald-500 mx-auto mb-3" />
                        <p className="text-sm text-emerald-700 font-medium">No alerts matching this filter</p>
                    </div>
                ) : (
                    filtered.map((alert, i) => {
                        const config = SEVERITY_CONFIG[alert.severity] || SEVERITY_CONFIG.INFO;
                        const AlertIcon = config.icon;
                        return (
                            <div key={i} className={`${config.bg} rounded-xl border ${config.border} p-5 transition-all hover:shadow-md`}>
                                <div className="flex items-start gap-4">
                                    <div className={`p-2 rounded-lg bg-white shadow-sm border ${config.border}`}>
                                        <AlertIcon size={20} className={config.iconColor} />
                                    </div>
                                    <div className="flex-1 min-w-0">
                                        <div className="flex items-center gap-2 mb-1">
                                            <span className={`inline-flex px-2 py-0.5 rounded border text-xs font-bold uppercase ${config.badge}`}>
                                                {alert.severity}
                                            </span>
                                            <span className="text-xs text-slate-400 font-medium uppercase">{alert.type}</span>
                                        </div>
                                        <h4 className="font-semibold text-slate-900 text-sm">{alert.title}</h4>
                                        <p className="text-xs text-slate-600 mt-1 leading-relaxed">{alert.message}</p>
                                        <div className="flex items-center gap-3 mt-2 text-xs text-slate-400">
                                            {alert.related_gstin !== 'N/A' && (
                                                <span className="font-mono">GSTIN: {alert.related_gstin?.slice(0, 12)}</span>
                                            )}
                                            {alert.related_invoice !== 'N/A' && (
                                                <span className="font-mono">Invoice: {alert.related_invoice}</span>
                                            )}
                                        </div>
                                    </div>
                                    <div className="flex-shrink-0">
                                        <span className={`inline-flex h-2 w-2 rounded-full ${alert.severity === 'CRITICAL' ? 'bg-rose-500 animate-pulse' : alert.severity === 'WARNING' ? 'bg-orange-400' : 'bg-slate-300'}`}></span>
                                    </div>
                                </div>
                            </div>
                        );
                    })
                )}
            </div>
        </div>
    );
}
