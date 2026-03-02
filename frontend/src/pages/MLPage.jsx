import React, { useState, useEffect, useCallback } from 'react';
import { RefreshCw, Brain, Target, BarChart3, Zap, Shield, AlertTriangle, CheckCircle, TrendingUp, Users } from 'lucide-react';
import { API } from '../config';

export default function MLPage() {
    const [predictions, setPredictions] = useState(null);
    const [metrics, setMetrics] = useState(null);
    const [featureImportance, setFeatureImportance] = useState(null);
    const [loading, setLoading] = useState(true);
    const [training, setTraining] = useState(false);
    const [activeView, setActiveView] = useState('predictions');

    const loadData = useCallback(async () => {
        setLoading(true);
        try {
            const res = await fetch(`${API}/api/v1/ml/predict-all`);
            const data = await res.json();
            setPredictions(data.predictions || []);
            setMetrics(data.model_metrics || {});
            setFeatureImportance(data.model_metrics?.feature_importance || {});
        } catch (err) {
            console.error('Failed to load ML predictions', err);
        }
        setLoading(false);
    }, []);

    useEffect(() => { loadData(); }, [loadData]);

    const handleTrain = async () => {
        setTraining(true);
        try {
            const res = await fetch(`${API}/api/v1/ml/train`, { method: 'POST' });
            const result = await res.json();
            setMetrics(result.metrics || {});
            setFeatureImportance(result.metrics?.feature_importance || {});
            await loadData();
        } catch (err) {
            console.error('Training failed', err);
        }
        setTraining(false);
    };

    if (loading) {
        return (
            <div className="flex items-center justify-center h-96">
                <Brain className="animate-pulse text-violet-600 mr-3" size={24} />
                <span className="text-slate-600 font-medium">Loading XGBoost predictions...</span>
            </div>
        );
    }

    const fraudCount = predictions?.filter(p => p.is_fraud_predicted === 1).length || 0;
    const cleanCount = predictions?.filter(p => p.is_fraud_predicted === 0).length || 0;
    const totalCount = predictions?.length || 0;

    const riskColor = (level) => {
        const map = {
            'CRITICAL': 'bg-rose-100 text-rose-700 border-rose-200',
            'HIGH': 'bg-orange-100 text-orange-700 border-orange-200',
            'MEDIUM': 'bg-amber-100 text-amber-700 border-amber-200',
            'LOW': 'bg-emerald-100 text-emerald-700 border-emerald-200',
        };
        return map[level] || map['LOW'];
    };

    const probColor = (prob) => {
        if (prob >= 0.85) return 'text-rose-600';
        if (prob >= 0.65) return 'text-orange-600';
        if (prob >= 0.35) return 'text-amber-600';
        return 'text-emerald-600';
    };

    const probBg = (prob) => {
        if (prob >= 0.85) return 'bg-rose-500';
        if (prob >= 0.65) return 'bg-orange-500';
        if (prob >= 0.35) return 'bg-amber-500';
        return 'bg-emerald-500';
    };

    // Get sorted feature importance entries (non-zero only, or top 8)
    const featureEntries = featureImportance
        ? Object.entries(featureImportance).sort((a, b) => b[1] - a[1]).slice(0, 10)
        : [];
    const maxImportance = featureEntries.length > 0 ? Math.max(...featureEntries.map(e => e[1]), 0.01) : 1;

    const formatFeatureName = (name) => name.replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase());

    const cm = metrics?.confusion_matrix || {};

    return (
        <div className="space-y-6">
            {/* Header */}
            <div className="flex justify-between items-center">
                <div>
                    <h2 className="text-xl font-bold text-slate-900 flex items-center gap-2">
                        <Brain size={22} className="text-violet-600" />
                        XGBoost ML Fraud Classifier
                    </h2>
                    <p className="text-sm text-slate-500 mt-1">
                        Gradient-boosted tree model trained on {metrics?.samples || 0} taxpayers with {Object.keys(featureImportance || {}).length} features
                    </p>
                </div>
                <button onClick={handleTrain} disabled={training}
                    className="flex items-center gap-2 px-4 py-2 bg-violet-600 text-white rounded-lg text-sm font-semibold hover:bg-violet-700 transition-colors shadow-md disabled:opacity-50">
                    {training ? <RefreshCw size={16} className="animate-spin" /> : <Zap size={16} />}
                    {training ? 'Training...' : 'Retrain Model'}
                </button>
            </div>

            {/* Model Performance Cards */}
            <div className="grid grid-cols-2 md:grid-cols-5 gap-4">
                <div className="bg-white rounded-xl border border-slate-200 p-4 shadow-sm">
                    <div className="flex items-center gap-2 mb-2">
                        <Target size={16} className="text-indigo-500" />
                        <p className="text-xs text-slate-500 font-semibold uppercase tracking-wider">Accuracy</p>
                    </div>
                    <p className="text-2xl font-bold text-slate-900">{((metrics?.accuracy || 0) * 100).toFixed(1)}%</p>
                </div>
                <div className="bg-white rounded-xl border border-slate-200 p-4 shadow-sm">
                    <div className="flex items-center gap-2 mb-2">
                        <BarChart3 size={16} className="text-emerald-500" />
                        <p className="text-xs text-slate-500 font-semibold uppercase tracking-wider">F1 Score</p>
                    </div>
                    <p className="text-2xl font-bold text-slate-900">{((metrics?.f1_score || 0) * 100).toFixed(1)}%</p>
                </div>
                <div className="bg-white rounded-xl border border-slate-200 p-4 shadow-sm">
                    <div className="flex items-center gap-2 mb-2">
                        <Shield size={16} className="text-rose-500" />
                        <p className="text-xs text-slate-500 font-semibold uppercase tracking-wider">Precision</p>
                    </div>
                    <p className="text-2xl font-bold text-slate-900">{((metrics?.precision || 0) * 100).toFixed(1)}%</p>
                </div>
                <div className="bg-white rounded-xl border border-slate-200 p-4 shadow-sm">
                    <div className="flex items-center gap-2 mb-2">
                        <TrendingUp size={16} className="text-amber-500" />
                        <p className="text-xs text-slate-500 font-semibold uppercase tracking-wider">Recall</p>
                    </div>
                    <p className="text-2xl font-bold text-slate-900">{((metrics?.recall || 0) * 100).toFixed(1)}%</p>
                </div>
                <div className="bg-white rounded-xl border border-slate-200 p-4 shadow-sm">
                    <div className="flex items-center gap-2 mb-2">
                        <Users size={16} className="text-violet-500" />
                        <p className="text-xs text-slate-500 font-semibold uppercase tracking-wider">CV F1</p>
                    </div>
                    <p className="text-2xl font-bold text-slate-900">
                        {metrics?.cv_f1_mean ? `${(metrics.cv_f1_mean * 100).toFixed(1)}%` : 'N/A'}
                    </p>
                    {metrics?.cv_f1_std !== undefined && (
                        <p className="text-xs text-slate-400 mt-1">±{(metrics.cv_f1_std * 100).toFixed(1)}%</p>
                    )}
                </div>
            </div>

            {/* View Tabs */}
            <div className="flex gap-2">
                {[
                    { key: 'predictions', label: 'Predictions', icon: Target },
                    { key: 'features', label: 'Feature Importance', icon: BarChart3 },
                    { key: 'confusion', label: 'Confusion Matrix', icon: Shield },
                ].map(tab => (
                    <button key={tab.key} onClick={() => setActiveView(tab.key)}
                        className={`flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium transition-colors ${activeView === tab.key
                            ? 'bg-violet-100 text-violet-700 border border-violet-200'
                            : 'bg-white text-slate-600 border border-slate-200 hover:bg-slate-50'
                            }`}>
                        <tab.icon size={16} />
                        {tab.label}
                    </button>
                ))}
            </div>

            {/* Predictions Table */}
            {activeView === 'predictions' && (
                <div className="bg-white rounded-xl border border-slate-200 shadow-sm overflow-hidden">
                    <div className="p-5 border-b border-slate-100 flex justify-between items-center">
                        <div>
                            <h3 className="font-semibold text-slate-900 text-lg">Fraud Predictions</h3>
                            <p className="text-xs text-slate-500 mt-1">
                                {fraudCount} flagged as fraud · {cleanCount} classified as clean · {totalCount} total
                            </p>
                        </div>
                        <div className="flex gap-2">
                            <span className="inline-flex items-center gap-1 px-2.5 py-1 bg-rose-50 border border-rose-200 rounded-full text-xs font-bold text-rose-700">
                                <AlertTriangle size={12} /> {fraudCount} Fraud
                            </span>
                            <span className="inline-flex items-center gap-1 px-2.5 py-1 bg-emerald-50 border border-emerald-200 rounded-full text-xs font-bold text-emerald-700">
                                <CheckCircle size={12} /> {cleanCount} Clean
                            </span>
                        </div>
                    </div>
                    <div className="overflow-x-auto">
                        <table className="min-w-full divide-y divide-slate-200">
                            <thead className="bg-slate-50">
                                <tr>
                                    <th className="px-4 py-3 text-left text-xs font-bold text-slate-500 uppercase">GSTIN</th>
                                    <th className="px-4 py-3 text-center text-xs font-bold text-slate-500 uppercase">Prediction</th>
                                    <th className="px-4 py-3 text-center text-xs font-bold text-slate-500 uppercase">Probability</th>
                                    <th className="px-4 py-3 text-center text-xs font-bold text-slate-500 uppercase">Risk Level</th>
                                    <th className="px-4 py-3 text-right text-xs font-bold text-slate-500 uppercase">Outward Value</th>
                                    <th className="px-4 py-3 text-right text-xs font-bold text-slate-500 uppercase">PageRank</th>
                                    <th className="px-4 py-3 text-center text-xs font-bold text-slate-500 uppercase">Degree (In/Out)</th>
                                </tr>
                            </thead>
                            <tbody className="divide-y divide-slate-100">
                                {(predictions || []).map((p, i) => (
                                    <tr key={i} className={`transition-colors ${p.is_fraud_predicted ? 'bg-rose-50/30 hover:bg-rose-50' : 'hover:bg-slate-50'}`}>
                                        <td className="px-4 py-3 font-mono text-sm text-slate-900 font-medium">{p.gstin}</td>
                                        <td className="px-4 py-3 text-center">
                                            {p.is_fraud_predicted ? (
                                                <span className="inline-flex items-center gap-1 px-2 py-0.5 bg-rose-100 text-rose-700 text-xs font-bold rounded border border-rose-200">
                                                    <AlertTriangle size={11} /> FRAUD
                                                </span>
                                            ) : (
                                                <span className="inline-flex items-center gap-1 px-2 py-0.5 bg-emerald-100 text-emerald-700 text-xs font-bold rounded border border-emerald-200">
                                                    <CheckCircle size={11} /> CLEAN
                                                </span>
                                            )}
                                        </td>
                                        <td className="px-4 py-3 text-center">
                                            <div className="flex items-center justify-center gap-2">
                                                <div className="w-20 bg-slate-100 rounded-full h-2 overflow-hidden">
                                                    <div className={`h-full rounded-full transition-all ${probBg(p.fraud_probability)}`}
                                                        style={{ width: `${p.fraud_probability * 100}%` }} />
                                                </div>
                                                <span className={`text-sm font-bold ${probColor(p.fraud_probability)}`}>
                                                    {(p.fraud_probability * 100).toFixed(1)}%
                                                </span>
                                            </div>
                                        </td>
                                        <td className="px-4 py-3 text-center">
                                            <span className={`inline-flex px-2 py-0.5 text-xs font-bold rounded border ${riskColor(p.risk_level)}`}>
                                                {p.risk_level}
                                            </span>
                                        </td>
                                        <td className="px-4 py-3 text-right text-sm font-semibold text-slate-900">
                                            ₹{(p.features?.total_outward_value || 0).toLocaleString('en-IN')}
                                        </td>
                                        <td className="px-4 py-3 text-right text-sm font-mono text-slate-600">
                                            {(p.features?.pagerank_score || 0).toFixed(4)}
                                        </td>
                                        <td className="px-4 py-3 text-center text-sm text-slate-600">
                                            {p.features?.in_degree || 0} / {p.features?.out_degree || 0}
                                        </td>
                                    </tr>
                                ))}
                            </tbody>
                        </table>
                    </div>
                </div>
            )}

            {/* Feature Importance */}
            {activeView === 'features' && (
                <div className="bg-white rounded-xl border border-slate-200 shadow-sm overflow-hidden">
                    <div className="p-5 border-b border-slate-100">
                        <h3 className="font-semibold text-slate-900 text-lg">Feature Importance</h3>
                        <p className="text-xs text-slate-500 mt-1">
                            XGBoost feature weights — higher values indicate stronger predictive power
                        </p>
                    </div>
                    <div className="p-5 space-y-3">
                        {featureEntries.map(([name, value], i) => (
                            <div key={name} className="flex items-center gap-4">
                                <div className="w-48 text-sm text-slate-700 font-medium truncate">
                                    {formatFeatureName(name)}
                                </div>
                                <div className="flex-1 bg-slate-100 rounded-full h-6 overflow-hidden relative">
                                    <div
                                        className={`h-full rounded-full transition-all duration-500 ${i === 0 ? 'bg-gradient-to-r from-violet-500 to-violet-600' :
                                            i < 3 ? 'bg-gradient-to-r from-indigo-400 to-indigo-500' :
                                                'bg-gradient-to-r from-slate-300 to-slate-400'
                                            }`}
                                        style={{ width: `${Math.max((value / maxImportance) * 100, 2)}%` }}
                                    />
                                    <span className="absolute inset-0 flex items-center justify-end pr-3 text-xs font-bold text-slate-700">
                                        {(value * 100).toFixed(1)}%
                                    </span>
                                </div>
                            </div>
                        ))}
                        {featureEntries.length === 0 && (
                            <p className="text-sm text-slate-400 text-center py-8">Train the model to see feature importance</p>
                        )}
                    </div>
                </div>
            )}

            {/* Confusion Matrix */}
            {activeView === 'confusion' && (
                <div className="bg-white rounded-xl border border-slate-200 shadow-sm overflow-hidden">
                    <div className="p-5 border-b border-slate-100">
                        <h3 className="font-semibold text-slate-900 text-lg">Confusion Matrix</h3>
                        <p className="text-xs text-slate-500 mt-1">
                            Model performance on training data — {metrics?.samples || 0} samples
                        </p>
                    </div>
                    <div className="p-8 flex justify-center">
                        <div className="relative">
                            {/* Labels */}
                            <div className="absolute -left-20 top-1/2 -translate-y-1/2 -rotate-90 text-xs font-bold text-slate-500 uppercase tracking-wider whitespace-nowrap">
                                Actual Label
                            </div>
                            <div className="text-center mb-3">
                                <span className="text-xs font-bold text-slate-500 uppercase tracking-wider">Predicted Label</span>
                            </div>

                            <div className="grid grid-cols-[auto_1fr_1fr] gap-0">
                                {/* Header */}
                                <div className="w-24" />
                                <div className="text-center py-2 text-sm font-bold text-emerald-700 bg-emerald-50 rounded-tl-lg border border-slate-200">
                                    Pred: Clean
                                </div>
                                <div className="text-center py-2 text-sm font-bold text-rose-700 bg-rose-50 rounded-tr-lg border-t border-r border-b border-slate-200">
                                    Pred: Fraud
                                </div>

                                {/* Row 1: Actual Clean */}
                                <div className="flex items-center justify-center py-6 px-3 text-sm font-bold text-emerald-700 bg-emerald-50 rounded-tl-lg border border-slate-200">
                                    Actual<br />Clean
                                </div>
                                <div className="flex flex-col items-center justify-center py-6 bg-emerald-50/50 border-b border-l border-slate-200">
                                    <span className="text-3xl font-bold text-emerald-700">{cm.true_negatives ?? 0}</span>
                                    <span className="text-xs text-emerald-600 mt-1 font-medium">True Negatives</span>
                                </div>
                                <div className="flex flex-col items-center justify-center py-6 bg-rose-50/30 border-b border-l border-r border-slate-200">
                                    <span className="text-3xl font-bold text-rose-400">{cm.false_positives ?? 0}</span>
                                    <span className="text-xs text-rose-500 mt-1 font-medium">False Positives</span>
                                </div>

                                {/* Row 2: Actual Fraud */}
                                <div className="flex items-center justify-center py-6 px-3 text-sm font-bold text-rose-700 bg-rose-50 rounded-bl-lg border-b border-l border-r border-slate-200">
                                    Actual<br />Fraud
                                </div>
                                <div className="flex flex-col items-center justify-center py-6 bg-amber-50/30 rounded-bl-lg border-b border-l border-slate-200">
                                    <span className="text-3xl font-bold text-amber-400">{cm.false_negatives ?? 0}</span>
                                    <span className="text-xs text-amber-600 mt-1 font-medium">False Negatives</span>
                                </div>
                                <div className="flex flex-col items-center justify-center py-6 bg-violet-50/50 rounded-br-lg border-b border-l border-r border-slate-200">
                                    <span className="text-3xl font-bold text-violet-700">{cm.true_positives ?? 0}</span>
                                    <span className="text-xs text-violet-600 mt-1 font-medium">True Positives</span>
                                </div>
                            </div>
                        </div>
                    </div>
                </div>
            )}
        </div>
    );
}
