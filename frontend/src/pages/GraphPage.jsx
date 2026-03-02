import React, { useState, useEffect } from 'react';
import { RefreshCw, ChevronRight, Shield } from 'lucide-react';
import NetworkGraph from '../NetworkGraph';
import { API } from '../config';

export default function GraphPage() {
    const [graphData, setGraphData] = useState({ nodes: [], links: [] });
    const [loading, setLoading] = useState(true);
    const [selectedNode, setSelectedNode] = useState(null);
    const [riskData, setRiskData] = useState(null);
    const [riskLoading, setRiskLoading] = useState(false);

    useEffect(() => {
        fetch(`${API}/api/graph-data`)
            .then(r => r.json())
            .then(d => { setGraphData(d); setLoading(false); })
            .catch(() => setLoading(false));
    }, []);

    const handleNodeSelect = (gstin) => {
        setSelectedNode(gstin);
        setRiskLoading(true);
        setRiskData(null);
        fetch(`${API}/api/v1/risk/vendor/${gstin}`)
            .then(r => r.json())
            .then(d => { setRiskData(d); setRiskLoading(false); })
            .catch(() => setRiskLoading(false));
    };

    const riskColor = (level) => {
        const colors = { CRITICAL: 'text-rose-600', HIGH: 'text-orange-600', MEDIUM: 'text-amber-600', LOW: 'text-emerald-600' };
        return colors[level] || 'text-slate-600';
    };

    const riskBg = (level) => {
        const colors = { CRITICAL: 'bg-rose-50 border-rose-200', HIGH: 'bg-orange-50 border-orange-200', MEDIUM: 'bg-amber-50 border-amber-200', LOW: 'bg-emerald-50 border-emerald-200' };
        return colors[level] || 'bg-slate-50 border-slate-200';
    };

    return (
        <div className="flex h-[calc(100vh-8rem)] gap-4">
            {/* Graph Canvas */}
            <div className="flex-1 bg-white rounded-xl border border-slate-200 shadow-sm overflow-hidden relative">
                <div className="absolute top-4 left-4 z-10 bg-white/90 backdrop-blur rounded-lg shadow-sm border border-slate-200 px-4 py-2">
                    <p className="text-xs text-slate-500 font-medium">
                        {graphData.nodes.length} nodes · {graphData.links.length} edges
                    </p>
                </div>

                <div className="w-full h-full relative bg-slate-50" style={{ backgroundImage: 'radial-gradient(#cbd5e1 1px, transparent 1px)', backgroundSize: '24px 24px' }}>
                    {loading ? (
                        <div className="absolute inset-0 flex items-center justify-center">
                            <RefreshCw className="animate-spin text-indigo-600 mr-3" size={24} />
                            <span className="text-slate-600 font-medium">Loading graph...</span>
                        </div>
                    ) : (
                        <NetworkGraph data={graphData} />
                    )}
                </div>

                {/* Legend */}
                <div className="absolute bottom-4 right-4 bg-white/90 backdrop-blur rounded-lg shadow-sm border border-slate-200 p-3 text-xs text-slate-500 z-10">
                    <div className="flex items-center gap-2 mb-1"><span className="w-2 h-2 rounded-full bg-rose-500"></span> Critical Risk</div>
                    <div className="flex items-center gap-2 mb-1"><span className="w-2 h-2 rounded-full bg-orange-400"></span> Warning</div>
                    <div className="flex items-center gap-2"><span className="w-2 h-2 rounded-full bg-slate-300"></span> Normal</div>
                </div>

                {/* Instructions */}
                <div className="absolute bottom-4 left-4 bg-white/90 backdrop-blur rounded-lg shadow-sm border border-slate-200 p-3 text-xs text-slate-400 z-10">
                    Click a node below to inspect · Scroll to zoom · Drag to pan
                </div>
            </div>

            {/* Right Panel — Node List + Details */}
            <div className="w-80 flex flex-col gap-4">
                {/* Vendor Risk Profile */}
                {(riskData || riskLoading) && (
                    <div className={`rounded-xl border shadow-sm overflow-hidden ${riskData ? riskBg(riskData.risk_level) : 'bg-white border-slate-200'}`}>
                        <div className="p-4 border-b border-slate-100 bg-white/80">
                            <div className="flex items-center gap-2 mb-1">
                                <Shield size={16} className={riskData ? riskColor(riskData.risk_level) : 'text-slate-400'} />
                                <h3 className="font-semibold text-sm text-slate-900">Vendor Profile</h3>
                            </div>
                            {riskLoading ? (
                                <div className="flex items-center gap-2 mt-2">
                                    <RefreshCw size={14} className="animate-spin text-indigo-600" />
                                    <span className="text-xs text-slate-500">Loading risk data...</span>
                                </div>
                            ) : riskData && (
                                <>
                                    <p className="text-xs font-mono text-slate-600 mt-1">{riskData.gstin}</p>
                                    <div className="flex items-center gap-2 mt-2">
                                        <span className={`text-2xl font-bold ${riskColor(riskData.risk_level)}`}>
                                            {(riskData.risk_score * 100).toFixed(0)}%
                                        </span>
                                        <span className={`px-2 py-0.5 rounded-full text-xs font-bold border ${riskBg(riskData.risk_level)} ${riskColor(riskData.risk_level)}`}>
                                            {riskData.risk_level}
                                        </span>
                                    </div>
                                </>
                            )}
                        </div>
                        {riskData && riskData.features && (
                            <div className="p-4 space-y-2 text-xs bg-white/50">
                                <div className="flex justify-between"><span className="text-slate-500">PageRank</span><span className="font-mono font-semibold">{riskData.features.pagerank_score}</span></div>
                                <div className="flex justify-between"><span className="text-slate-500">In-Degree</span><span className="font-mono font-semibold">{riskData.features.in_degree}</span></div>
                                <div className="flex justify-between"><span className="text-slate-500">Out-Degree</span><span className="font-mono font-semibold">{riskData.features.out_degree}</span></div>
                                <div className="flex justify-between"><span className="text-slate-500">ITC/Sales Ratio</span><span className="font-mono font-semibold">{riskData.features.itc_to_sales_ratio}</span></div>
                                <div className="flex justify-between"><span className="text-slate-500">Zero Cash Months</span><span className="font-mono font-semibold">{riskData.features.zero_cash_tax_months}</span></div>
                                <div className="flex justify-between"><span className="text-slate-500">Outward Value</span><span className="font-mono font-semibold">₹{riskData.features.total_outward_value?.toLocaleString('en-IN')}</span></div>
                                {riskData.features.is_known_fraud === 1 && (
                                    <div className="mt-2 px-2 py-1 bg-rose-100 rounded text-rose-700 font-bold text-center">
                                        ⚠️ Known Fraud: {riskData.features.fraud_type}
                                    </div>
                                )}
                            </div>
                        )}
                    </div>
                )}

                {/* Node List */}
                <div className="flex-1 bg-white rounded-xl border border-slate-200 shadow-sm overflow-hidden flex flex-col">
                    <div className="p-4 border-b border-slate-100">
                        <h3 className="font-semibold text-sm text-slate-900">Taxpayer Nodes</h3>
                        <p className="text-xs text-slate-400 mt-0.5">{graphData.nodes.length} entities</p>
                    </div>
                    <div className="flex-1 overflow-y-auto">
                        {graphData.nodes.map((node, i) => {
                            const levelColor = node.riskLevel === 'critical' ? 'text-rose-500' : node.riskLevel === 'warning' ? 'text-orange-500' : 'text-slate-400';
                            return (
                                <button key={i} onClick={() => handleNodeSelect(node.id)}
                                    className={`w-full text-left px-4 py-3 border-b border-slate-50 hover:bg-slate-50 transition-colors flex items-center gap-3 ${selectedNode === node.id ? 'bg-indigo-50 border-l-2 border-l-indigo-600' : ''}`}>
                                    <span className={`w-2 h-2 rounded-full ${node.riskLevel === 'critical' ? 'bg-rose-500' : node.riskLevel === 'warning' ? 'bg-orange-400' : 'bg-slate-300'}`}></span>
                                    <div className="flex-1 min-w-0">
                                        <p className="text-xs font-mono text-slate-900 truncate">{node.id}</p>
                                        <p className="text-xs text-slate-400 truncate">{node.label}</p>
                                    </div>
                                    <ChevronRight size={14} className="text-slate-300" />
                                </button>
                            );
                        })}
                    </div>
                </div>
            </div>
        </div>
    );
}
