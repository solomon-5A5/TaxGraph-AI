import React, { useState, useEffect, useRef } from 'react';
import {
    Receipt, CheckCircle, AlertTriangle, TrendingUp, TrendingDown,
    RefreshCw, Calendar, Download, Shield, Building2, Network, Activity, Zap
} from 'lucide-react';
import {
    PieChart, Pie, Cell, BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip,
    ResponsiveContainer, Legend
} from 'recharts';
import NetworkGraph from '../NetworkGraph';

const API = 'http://127.0.0.1:8000';

/* ── Animated Number Counter ── */
function AnimatedNumber({ value, duration = 1200, prefix = '', suffix = '' }) {
    const [display, setDisplay] = useState(0);
    const ref = useRef(null);
    useEffect(() => {
        const num = typeof value === 'number' ? value : parseInt(String(value).replace(/[^0-9]/g, ''), 10) || 0;
        if (num === 0) { setDisplay(0); return; }
        let start = 0;
        const startTime = performance.now();
        const animate = (now) => {
            const elapsed = now - startTime;
            const progress = Math.min(elapsed / duration, 1);
            const eased = 1 - Math.pow(1 - progress, 3); // ease-out cubic
            setDisplay(Math.floor(eased * num));
            if (progress < 1) ref.current = requestAnimationFrame(animate);
        };
        ref.current = requestAnimationFrame(animate);
        return () => cancelAnimationFrame(ref.current);
    }, [value, duration]);
    return <>{prefix}{display.toLocaleString('en-IN')}{suffix}</>;
}

/* ── Metric Card with Animated Value ── */
const MetricCard = ({ title, value, icon: Icon, trendStr, isTrendUp, iconBg, iconColor, trendColor, trendBg, progressColor, progressWidth }) => (
    <div className="bg-white rounded-xl p-5 border border-slate-200 shadow-sm hover:shadow-md transition-all duration-300 hover:-translate-y-0.5">
        <div className="flex justify-between items-start mb-4">
            <div className={`p-2 rounded-lg ${iconBg} ${iconColor}`}><Icon size={24} /></div>
            <span className={`flex items-center px-2 py-0.5 rounded-full text-xs font-semibold ${trendColor} ${trendBg}`}>
                {isTrendUp ? <TrendingUp size={14} className="mr-1" /> : <TrendingDown size={14} className="mr-1" />}
                {trendStr}
            </span>
        </div>
        <div>
            <p className="text-slate-500 text-sm font-medium">{title}</p>
            <h3 className="text-slate-900 text-2xl font-bold mt-1">
                <AnimatedNumber value={value} />
            </h3>
        </div>
        <div className="mt-4 h-1.5 w-full bg-slate-100 rounded-full overflow-hidden">
            <div className={`h-full rounded-full ${progressColor} transition-all duration-1000 ease-out`} style={{ width: progressWidth }}></div>
        </div>
    </div>
);

/* ── Chart Colors ── */
const CHART_COLORS = ['#6366f1', '#10b981', '#f59e0b', '#ef4444', '#8b5cf6', '#06b6d4'];
const PIE_COLORS = ['#10b981', '#ef4444', '#f97316', '#eab308'];

/* ── Skeleton Loader ── */
const SkeletonCard = () => (
    <div className="bg-white rounded-xl p-5 border border-slate-200 shadow-sm animate-pulse">
        <div className="flex justify-between items-start mb-4">
            <div className="w-10 h-10 bg-slate-200 rounded-lg" />
            <div className="w-16 h-5 bg-slate-200 rounded-full" />
        </div>
        <div className="w-20 h-3 bg-slate-200 rounded mb-2" />
        <div className="w-16 h-7 bg-slate-200 rounded" />
        <div className="mt-4 h-1.5 w-full bg-slate-100 rounded-full" />
    </div>
);

export default function DashboardPage() {
    const [graphData, setGraphData] = useState({ nodes: [], links: [] });
    const [aiInsight, setAiInsight] = useState("Initializing AI Engine...");
    const [aiConfidence, setAiConfidence] = useState(null);
    const [aiModel, setAiModel] = useState(null);
    const [fraudTable, setFraudTable] = useState([]);
    const [stats, setStats] = useState(null);
    const [anomalyStats, setAnomalyStats] = useState(null);
    const [isLoading, setIsLoading] = useState(true);

    useEffect(() => {
        Promise.all([
            fetch(`${API}/api/graph-data`).then(r => r.json()),
            fetch(`${API}/api/v1/stats`).then(r => r.json()),
            fetch(`${API}/api/v1/anomalies`).then(r => r.json()).catch(() => null),
        ]).then(([graphRes, statsRes, anomalyRes]) => {
            setGraphData(graphRes);
            setStats(statsRes);
            if (anomalyRes) setAnomalyStats(anomalyRes);
            setIsLoading(false);
        }).catch(() => setIsLoading(false));

        fetch(`${API}/api/ai-insight`)
            .then(r => r.json())
            .then(data => {
                setAiInsight(data.insight);
                setFraudTable(data.fraud_table || []);
                if (data.confidence) setAiConfidence(data.confidence);
                if (data.model) setAiModel(data.model);
            })
            .catch(() => setAiInsight("AI Engine Offline."));
    }, []);

    /* ── Build chart data from stats ── */
    const reconPieData = stats ? [
        { name: 'Reconciled', value: stats.reconciliation?.fully_reconciled || 0 },
        { name: 'Missing GSTR-1', value: stats.reconciliation?.missing_in_gstr1 || 0 },
        { name: 'Value Mismatch', value: stats.reconciliation?.value_mismatch || 0 },
        { name: 'Tax Mismatch', value: stats.reconciliation?.tax_mismatch || 0 },
    ].filter(d => d.value > 0) : [];

    const fraudBarData = stats?.fraud_summary ? [
        { name: 'Circular', count: stats.fraud_summary.circular_count || 0 },
        { name: 'Shell', count: stats.fraud_summary.shell_count || 0 },
        { name: 'Reciprocal', count: stats.fraud_summary.reciprocal_count || 0 },
        { name: 'Fake Inv.', count: stats.fraud_summary.fake_invoice_count || 0 },
    ] : [];

    const handleExport = async () => {
        try {
            const res = await fetch(`${API}/api/v1/export/risk-leaderboard`);
            const json = await res.json();
            const rows = json.data || [];
            if (rows.length === 0) return;
            const headers = Object.keys(rows[0]);
            const csv = [headers.join(','), ...rows.map(r => headers.map(h => `"${r[h] ?? ''}"`).join(','))].join('\n');
            const blob = new Blob([csv], { type: 'text/csv' });
            const url = URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url; a.download = `risk-leaderboard-${new Date().toISOString().slice(0,10)}.csv`;
            a.click(); URL.revokeObjectURL(url);
        } catch { /* silently fail */ }
    };

    return (
        <div className="space-y-6">
            {/* Date Filter & Actions */}
            <div className="flex justify-between items-center mb-2">
                <div className="flex items-center gap-2 text-sm text-slate-500">
                    <span>Last updated: just now</span>
                    {isLoading ? <RefreshCw size={14} className="animate-spin text-indigo-600" /> : <RefreshCw size={14} />}
                </div>
                <div className="flex gap-2">
                    <button className="flex items-center gap-2 px-3 py-1.5 bg-white border border-slate-200 rounded-lg text-sm font-medium text-slate-600 shadow-sm hover:bg-slate-50 transition-colors"><Calendar size={16} /> This Month</button>
                    <button onClick={handleExport} className="flex items-center gap-2 px-3 py-1.5 bg-indigo-600 text-white rounded-lg text-sm font-medium shadow-sm hover:bg-indigo-700 transition-colors"><Download size={16} /> Export CSV</button>
                </div>
            </div>

            {/* KPI Metric Cards */}
            {isLoading ? (
                <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-4 gap-4">
                    {[...Array(4)].map((_, i) => <SkeletonCard key={i} />)}
                </div>
            ) : (
                <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-4 gap-4">
                    <MetricCard title="Total Invoices" value={stats?.total_invoices ?? graphData.links.length ?? 0} icon={Receipt} trendStr={`${stats?.reconciliation?.reconciliation_rate ?? 0}% match`} isTrendUp={true} iconBg="bg-indigo-50" iconColor="text-indigo-600" trendColor="text-emerald-600" trendBg="bg-emerald-50" progressColor="bg-indigo-600" progressWidth={`${stats?.reconciliation?.reconciliation_rate ?? 70}%`} />
                    <MetricCard title="Active Taxpayers" value={stats?.active_taxpayers || stats?.total_taxpayers || graphData.nodes.length || 0} icon={Building2} trendStr="Active" isTrendUp={true} iconBg="bg-emerald-50" iconColor="text-emerald-600" trendColor="text-emerald-600" trendBg="bg-emerald-50" progressColor="bg-emerald-500" progressWidth="88%" />
                    <MetricCard title="Mismatched" value={stats?.total_mismatches ?? 0} icon={AlertTriangle} trendStr={`${stats?.reconciliation?.value_mismatch ?? 0} value`} isTrendUp={false} iconBg="bg-orange-50" iconColor="text-orange-500" trendColor="text-orange-600" trendBg="bg-orange-50" progressColor="bg-orange-400" progressWidth={`${Math.min((stats?.total_mismatches || 0) / Math.max(stats?.total_invoices || 1, 1) * 100, 100)}%`} />
                    <MetricCard title="Fraud Flags" value={stats?.fraud_flags ?? 0} icon={Shield} trendStr={`${stats?.critical_alerts ?? 0} critical`} isTrendUp={true} iconBg="bg-rose-50" iconColor="text-rose-500" trendColor="text-rose-600" trendBg="bg-rose-50" progressColor="bg-rose-500" progressWidth={`${Math.min((stats?.fraud_flags || 0) * 5, 100)}%`} />
                </div>
            )}

            {/* Charts Row — Reconciliation Pie + Fraud Bar */}
            {!isLoading && (reconPieData.length > 0 || fraudBarData.length > 0) && (
                <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                    {/* Reconciliation Pie Chart */}
                    {reconPieData.length > 0 && (
                        <div className="bg-white rounded-xl border border-slate-200 shadow-sm p-5">
                            <h3 className="font-semibold text-slate-900 mb-1">Reconciliation Breakdown</h3>
                            <p className="text-xs text-slate-500 mb-4">GSTR-1 ↔ GSTR-2B match distribution</p>
                            <ResponsiveContainer width="100%" height={240}>
                                <PieChart>
                                    <Pie data={reconPieData} cx="50%" cy="50%" innerRadius={55} outerRadius={90} paddingAngle={3} dataKey="value" label={({ name, percent }) => `${name} ${(percent * 100).toFixed(0)}%`} labelLine={false}>
                                        {reconPieData.map((_, i) => (
                                            <Cell key={i} fill={PIE_COLORS[i % PIE_COLORS.length]} />
                                        ))}
                                    </Pie>
                                    <Tooltip formatter={(val) => val.toLocaleString('en-IN')} />
                                    <Legend verticalAlign="bottom" height={36} iconType="circle" />
                                </PieChart>
                            </ResponsiveContainer>
                        </div>
                    )}

                    {/* Fraud Pattern Bar Chart */}
                    {fraudBarData.length > 0 && (
                        <div className="bg-white rounded-xl border border-slate-200 shadow-sm p-5">
                            <h3 className="font-semibold text-slate-900 mb-1">Fraud Pattern Distribution</h3>
                            <p className="text-xs text-slate-500 mb-4">Detection count by algorithm type</p>
                            <ResponsiveContainer width="100%" height={240}>
                                <BarChart data={fraudBarData} barCategoryGap="20%">
                                    <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
                                    <XAxis dataKey="name" tick={{ fontSize: 12, fill: '#64748b' }} />
                                    <YAxis tick={{ fontSize: 12, fill: '#64748b' }} allowDecimals={false} />
                                    <Tooltip formatter={(val) => [val, 'Detections']} />
                                    <Bar dataKey="count" radius={[6, 6, 0, 0]}>
                                        {fraudBarData.map((_, i) => (
                                            <Cell key={i} fill={CHART_COLORS[i % CHART_COLORS.length]} />
                                        ))}
                                    </Bar>
                                </BarChart>
                            </ResponsiveContainer>
                        </div>
                    )}
                </div>
            )}

            {/* Anomaly Detection Banner */}
            {anomalyStats && anomalyStats.summary?.total_anomalies > 0 && (
                <div className="bg-gradient-to-r from-purple-50 to-indigo-50 rounded-xl border border-purple-200 shadow-sm p-5">
                    <div className="flex items-center justify-between">
                        <div className="flex items-center gap-3">
                            <div className="p-2 bg-purple-100 rounded-lg"><Activity size={22} className="text-purple-600" /></div>
                            <div>
                                <h3 className="font-semibold text-slate-900">Statistical Anomaly Detection</h3>
                                <p className="text-xs text-slate-500 mt-0.5">Z-score & IQR analysis across invoices and vendors</p>
                            </div>
                        </div>
                        <div className="flex gap-4">
                            <div className="text-center">
                                <p className="text-2xl font-bold text-purple-700"><AnimatedNumber value={anomalyStats.summary.total_anomalies} /></p>
                                <p className="text-xs text-slate-500">Total Anomalies</p>
                            </div>
                            <div className="text-center">
                                <p className="text-2xl font-bold text-rose-600"><AnimatedNumber value={anomalyStats.summary.unique_entities} /></p>
                                <p className="text-xs text-slate-500">Unique Entities</p>
                            </div>
                            <div className="text-center">
                                <p className="text-2xl font-bold text-amber-600"><AnimatedNumber value={anomalyStats.invoice_anomalies?.length || 0} /></p>
                                <p className="text-xs text-slate-500">Invoice Outliers</p>
                            </div>
                        </div>
                    </div>
                </div>
            )}

            {/* Main Grid — Graph + AI Insight */}
            <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 h-[600px]">
                {/* GRAPH ANALYSIS CANVAS */}
                <div className="lg:col-span-2 bg-white rounded-xl border border-slate-200 shadow-sm flex flex-col overflow-hidden relative group">
                    <div className="p-5 border-b border-slate-100 flex justify-between items-center z-10 bg-white">
                        <div>
                            <h3 className="font-semibold text-slate-900">Network Graph Analysis</h3>
                            <p className="text-xs text-slate-500 mt-1">Visualizing entity relationships and circular trading patterns</p>
                        </div>
                        <div className="flex gap-2">
                            <span className="text-xs text-slate-400 px-2 py-1 bg-slate-50 rounded-md font-medium">{graphData.nodes.length} nodes · {graphData.links.length} edges</span>
                        </div>
                    </div>
                    <div className="flex-1 w-full h-full relative bg-slate-50" style={{ backgroundImage: 'radial-gradient(#cbd5e1 1px, transparent 1px)', backgroundSize: '24px 24px' }}>
                        {isLoading ? (
                            <div className="absolute inset-0 flex flex-col items-center justify-center bg-slate-50/80 z-20">
                                <RefreshCw className="animate-spin text-indigo-600 mb-4" size={32} />
                                <p className="text-slate-600 font-medium">Ingesting Live Graph Data...</p>
                            </div>
                        ) : (
                            <NetworkGraph data={graphData} />
                        )}
                        <div className="absolute bottom-4 right-4 bg-white/90 backdrop-blur rounded-lg shadow-sm border border-slate-200 p-2 text-xs text-slate-500 z-10 pointer-events-none">
                            <div className="flex items-center gap-2 mb-1"><span className="w-2 h-2 rounded-full bg-rose-500"></span> Critical Risk</div>
                            <div className="flex items-center gap-2 mb-1"><span className="w-2 h-2 rounded-full bg-orange-400"></span> Warning</div>
                            <div className="flex items-center gap-2"><span className="w-2 h-2 rounded-full bg-slate-300"></span> Normal</div>
                        </div>
                    </div>
                </div>

                {/* AI INSIGHTS */}
                <div className="bg-white rounded-xl border border-slate-200 shadow-sm flex flex-col overflow-hidden">
                    <div className="p-5 border-b border-slate-100 flex justify-between items-center bg-white">
                        <h3 className="font-semibold text-slate-900 flex items-center gap-2">✨ AI Analysis</h3>
                        <div className="flex items-center gap-2">
                            {aiConfidence && (
                                <span className="px-2 py-0.5 bg-indigo-100 text-indigo-700 text-xs font-bold rounded-full border border-indigo-200">
                                    {aiConfidence}% conf
                                </span>
                            )}
                            <span className="relative flex h-3 w-3">
                                <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-indigo-400 opacity-75"></span>
                                <span className="relative inline-flex rounded-full h-3 w-3 bg-indigo-600"></span>
                            </span>
                        </div>
                    </div>
                    <div className="flex-1 overflow-y-auto p-5 bg-gradient-to-b from-indigo-50/50 to-white">
                        {isLoading ? (
                            <div className="animate-pulse flex flex-col gap-3">
                                <div className="h-4 bg-indigo-100 rounded w-3/4"></div>
                                <div className="h-4 bg-indigo-100 rounded w-full"></div>
                                <div className="h-4 bg-indigo-100 rounded w-5/6"></div>
                            </div>
                        ) : (
                            <div>
                                <div className="flex items-center gap-2 mb-3">
                                    <span className="inline-block px-3 py-1 bg-rose-100 text-rose-700 text-xs font-bold rounded-full border border-rose-200 uppercase tracking-wider">
                                        Critical Threat Detected
                                    </span>
                                    {aiModel && (
                                        <span className="inline-block px-2 py-0.5 bg-slate-100 text-slate-500 text-xs font-medium rounded-full border border-slate-200">
                                            <Zap size={10} className="inline mr-0.5" />{aiModel}
                                        </span>
                                    )}
                                </div>
                                <p className="text-sm text-slate-700 leading-relaxed font-medium mb-4">{aiInsight}</p>

                                {fraudTable && fraudTable.length > 0 && (
                                    <div className="overflow-hidden rounded-lg border border-slate-200 shadow-sm mb-4">
                                        <table className="min-w-full divide-y divide-slate-200">
                                            <thead className="bg-slate-50">
                                                <tr>
                                                    <th className="px-3 py-2 text-left text-xs font-bold text-slate-500 uppercase tracking-wider">GSTIN</th>
                                                    <th className="px-3 py-2 text-left text-xs font-bold text-slate-500 uppercase tracking-wider">Role</th>
                                                    <th className="px-3 py-2 text-right text-xs font-bold text-slate-500 uppercase tracking-wider">Value</th>
                                                </tr>
                                            </thead>
                                            <tbody className="bg-white divide-y divide-slate-200 text-xs">
                                                {fraudTable.map((row, index) => (
                                                    <tr key={index} className="hover:bg-slate-50 transition-colors">
                                                        <td className="px-3 py-2 whitespace-nowrap font-mono text-slate-900">{row.gstin.slice(0, 12)}</td>
                                                        <td className="px-3 py-2 whitespace-nowrap">
                                                            <span className={`inline-flex px-2 py-0.5 rounded-full text-xs font-semibold ${row.role.includes('Mastermind') ? 'bg-red-100 text-red-700' : 'bg-orange-100 text-orange-700'}`}>
                                                                {row.role}
                                                            </span>
                                                        </td>
                                                        <td className="px-3 py-2 text-right font-semibold text-slate-900">{row.formatted_value}</td>
                                                    </tr>
                                                ))}
                                            </tbody>
                                        </table>
                                    </div>
                                )}

                                {/* Fraud Summary Cards */}
                                {stats && (
                                    <div className="grid grid-cols-2 gap-2 mb-4">
                                        <div className="bg-rose-50 rounded-lg p-3 border border-rose-100">
                                            <p className="text-xs text-rose-500 font-medium">Circular Trades</p>
                                            <p className="text-lg font-bold text-rose-700">{stats.fraud_summary?.circular_count ?? 0}</p>
                                        </div>
                                        <div className="bg-orange-50 rounded-lg p-3 border border-orange-100">
                                            <p className="text-xs text-orange-500 font-medium">Reciprocal</p>
                                            <p className="text-lg font-bold text-orange-700">{stats.fraud_summary?.reciprocal_count ?? 0}</p>
                                        </div>
                                    </div>
                                )}

                                <button className="mt-2 w-full py-2 bg-indigo-600 text-white text-sm font-semibold rounded-lg shadow-md hover:bg-indigo-700 transition-colors">
                                    Generate DRC-01 Show Cause Notice
                                </button>
                            </div>
                        )}
                    </div>
                </div>
            </div>
        </div>
    );
}
