import React, { useState, useEffect, useRef, useCallback } from 'react';
import { BrowserRouter, Routes, Route, NavLink, useLocation, useNavigate } from 'react-router-dom';
import {
  Network, LayoutDashboard, Receipt, Bell, Plus,
  RefreshCw, Search, Shield, MessageSquare, AlertTriangle,
  Activity, X, CheckCircle, XCircle, Info, History
} from 'lucide-react';

import DashboardPage from './pages/DashboardPage';
import ReconciliationPage from './pages/ReconciliationPage';
import FraudPage from './pages/FraudPage';
import GraphPage from './pages/GraphPage';
import AlertsPage from './pages/AlertsPage';
import QueryPage from './pages/QueryPage';
import AnomalyPage from './pages/AnomalyPage';

const API = 'http://127.0.0.1:8000';

const NAV_ITEMS = [
  { to: '/', label: 'Dashboard', icon: LayoutDashboard },
  { to: '/reconciliation', label: 'Reconciliation', icon: Receipt },
  { to: '/graph', label: 'Graph Analysis', icon: Network },
  { to: '/fraud', label: 'Fraud Detection', icon: Shield },
  { to: '/anomalies', label: 'Anomalies', icon: Activity },
  { to: '/alerts', label: 'Alerts', icon: Bell, badge: true },
  { to: '/query', label: 'NL Query', icon: MessageSquare },
];

/* ── Toast Notification System ── */
const ToastContext = React.createContext(() => {});
export const useToast = () => React.useContext(ToastContext);

function ToastContainer({ toasts, removeToast }) {
  const iconMap = { success: CheckCircle, error: XCircle, info: Info, warning: AlertTriangle };
  const colorMap = {
    success: 'bg-emerald-50 border-emerald-200 text-emerald-800',
    error: 'bg-rose-50 border-rose-200 text-rose-800',
    info: 'bg-indigo-50 border-indigo-200 text-indigo-800',
    warning: 'bg-amber-50 border-amber-200 text-amber-800',
  };
  const iconColorMap = { success: 'text-emerald-500', error: 'text-rose-500', info: 'text-indigo-500', warning: 'text-amber-500' };

  return (
    <div className="fixed bottom-20 right-6 z-[100] flex flex-col gap-2 pointer-events-none">
      {toasts.map(t => {
        const Icon = iconMap[t.type] || Info;
        return (
          <div key={t.id}
            className={`pointer-events-auto flex items-center gap-3 px-4 py-3 rounded-xl border shadow-lg backdrop-blur-sm animate-slide-in-right ${colorMap[t.type] || colorMap.info}`}>
            <Icon size={18} className={iconColorMap[t.type]} />
            <span className="text-sm font-medium flex-1">{t.message}</span>
            <button onClick={() => removeToast(t.id)} className="opacity-50 hover:opacity-100 transition-opacity">
              <X size={14} />
            </button>
          </div>
        );
      })}
    </div>
  );
}

function AppLayout() {
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [isUploading, setIsUploading] = useState(false);
  const [toasts, setToasts] = useState([]);
  const [backendStatus, setBackendStatus] = useState('checking');
  const [searchOpen, setSearchOpen] = useState(false);
  const [searchQuery, setSearchQuery] = useState('');
  const [searchResults, setSearchResults] = useState([]);
  const [searchLoading, setSearchLoading] = useState(false);
  const searchRef = useRef(null);
  const searchInputRef = useRef(null);
  const location = useLocation();
  const navigate = useNavigate();

  // Toast management
  const addToast = useCallback((message, type = 'info') => {
    const id = Date.now() + Math.random();
    setToasts(prev => [...prev, { id, message, type }]);
    setTimeout(() => setToasts(prev => prev.filter(t => t.id !== id)), 4000);
  }, []);

  const removeToast = useCallback((id) => {
    setToasts(prev => prev.filter(t => t.id !== id));
  }, []);

  // Backend health check
  useEffect(() => {
    const check = () => {
      fetch(`${API}/api/v1/stats`, { signal: AbortSignal.timeout(3000) })
        .then(r => r.ok ? setBackendStatus('online') : setBackendStatus('error'))
        .catch(() => setBackendStatus('offline'));
    };
    check();
    const interval = setInterval(check, 30000);
    return () => clearInterval(interval);
  }, []);

  // ⌘K keyboard shortcut
  useEffect(() => {
    const handler = (e) => {
      if ((e.metaKey || e.ctrlKey) && e.key === 'k') {
        e.preventDefault();
        setSearchOpen(prev => !prev);
      }
      if (e.key === 'Escape') setSearchOpen(false);
    };
    window.addEventListener('keydown', handler);
    return () => window.removeEventListener('keydown', handler);
  }, []);

  useEffect(() => {
    if (searchOpen && searchInputRef.current) searchInputRef.current.focus();
  }, [searchOpen]);

  // Search debounce
  useEffect(() => {
    if (!searchQuery || searchQuery.length < 2) { setSearchResults([]); return; }
    setSearchLoading(true);
    const timer = setTimeout(() => {
      fetch(`${API}/api/v1/search/${encodeURIComponent(searchQuery)}`)
        .then(r => r.json())
        .then(d => { setSearchResults(d.results || []); setSearchLoading(false); })
        .catch(() => { setSearchResults([]); setSearchLoading(false); });
    }, 300);
    return () => clearTimeout(timer);
  }, [searchQuery]);

  // Close search on click outside
  useEffect(() => {
    const handler = (e) => {
      if (searchRef.current && !searchRef.current.contains(e.target)) setSearchOpen(false);
    };
    document.addEventListener('mousedown', handler);
    return () => document.removeEventListener('mousedown', handler);
  }, []);

  // Page title based on route
  const getTitle = () => {
    const titles = {
      '/': 'Dashboard Overview',
      '/reconciliation': 'Invoice Reconciliation',
      '/graph': 'Network Graph Analysis',
      '/fraud': 'Fraud Detection Engine',
      '/anomalies': 'Statistical Anomaly Detection',
      '/alerts': 'Alert Center',
      '/query': 'Natural Language Query',
    };
    return titles[location.pathname] || 'Dashboard';
  };

  const handleUpload = async (e) => {
    e.preventDefault();
    setIsUploading(true);
    addToast('Uploading forensic data...', 'info');

    const formData = new FormData();
    formData.append('taxpayers', e.target.taxpayers.files[0]);
    formData.append('gstr1', e.target.gstr1.files[0]);
    formData.append('gstr2b', e.target.gstr2b.files[0]);
    formData.append('gstr3b', e.target.gstr3b.files[0]);
    formData.append('fraud_labels', e.target.fraud_labels.files[0]);

    try {
      await fetch(`${API}/api/upload`, { method: 'POST', body: formData });
      await fetch(`${API}/api/v1/reload`, { method: 'POST' });
      setIsModalOpen(false);
      addToast('Data uploaded and graph rebuilt successfully!', 'success');
      setTimeout(() => window.location.reload(), 1000);
    } catch (err) {
      console.error("Upload failed", err);
      addToast('Upload failed — check backend connection', 'error');
    }
    setIsUploading(false);
  };

  const handleSearchSelect = (gstin) => {
    setSearchOpen(false);
    setSearchQuery('');
    navigate('/graph');
    addToast(`Navigating to graph view for ${gstin}`, 'info');
  };

  const statusColor = backendStatus === 'online' ? 'bg-emerald-500' : backendStatus === 'offline' ? 'bg-rose-500' : 'bg-amber-500';
  const statusLabel = backendStatus === 'online' ? 'API Online' : backendStatus === 'offline' ? 'API Offline' : 'Checking...';

  return (
    <ToastContext.Provider value={addToast}>
      <div className="bg-slate-50 text-slate-900 overflow-hidden h-screen flex font-sans">
        {/* SIDEBAR */}
        <aside className="w-64 bg-white border-r border-slate-200 flex flex-col h-full flex-shrink-0 z-20 shadow-sm">
          <div className="p-6 flex items-center gap-3">
            <div className="bg-gradient-to-br from-indigo-600 to-indigo-800 rounded-lg w-8 h-8 flex items-center justify-center text-white shadow-lg shadow-indigo-600/30">
              <Network size={20} />
            </div>
            <div>
              <h1 className="text-slate-900 font-semibold text-sm leading-tight">TaxGraph AI</h1>
              <p className="text-slate-500 text-xs font-normal">Enterprise</p>
            </div>
          </div>

          <div className="px-4 flex flex-col gap-1 mt-2">
            <div className="mb-4">
              <p className="px-4 text-xs font-semibold text-slate-400 uppercase tracking-wider mb-2">Platform</p>
              {NAV_ITEMS.map(item => (
                <NavLink key={item.to} to={item.to} end={item.to === '/'}
                  className={({ isActive }) =>
                    `flex items-center gap-3 px-4 py-2.5 rounded-full transition-colors ${isActive ? 'bg-slate-100 text-indigo-600 font-medium' : 'text-slate-600 hover:bg-slate-50 hover:text-slate-900'}`
                  }>
                  <item.icon size={20} />
                  <span className="text-sm flex-1">{item.label}</span>
                  {item.badge && (
                    <span className="bg-rose-100 text-rose-600 text-xs font-bold px-1.5 py-0.5 rounded-md">!</span>
                  )}
                </NavLink>
              ))}
            </div>
          </div>

          <div className="mt-auto p-4 border-t border-slate-100">
            <button
              onClick={() => setIsModalOpen(true)}
              className="w-full bg-indigo-600 hover:bg-indigo-700 text-white text-sm font-semibold py-2.5 rounded-full shadow-lg shadow-indigo-600/25 transition-all flex items-center justify-center gap-2">
              <Plus size={18} /> New Analysis
            </button>
          </div>
        </aside>

        {/* MAIN CONTENT */}
        <main className="flex-1 flex flex-col min-w-0 overflow-hidden bg-slate-50">
          {/* Header */}
          <header className="h-16 bg-white/80 backdrop-blur-md border-b border-slate-200 flex items-center justify-between px-8 sticky top-0 z-10">
            <h2 className="text-slate-800 text-lg font-semibold tracking-tight">{getTitle()}</h2>
            <div className="flex items-center gap-4">
              <div className="relative" ref={searchRef}>
                <button onClick={() => setSearchOpen(true)}
                  className="flex items-center gap-2 w-64 pl-3 pr-3 py-1.5 border-none rounded-lg bg-slate-100 text-slate-500 hover:bg-slate-200/70 transition-all text-sm cursor-pointer text-left">
                  <Search size={16} className="text-slate-400" />
                  <span className="flex-1">Search GSTINs...</span>
                  <span className="text-slate-400 text-xs border border-slate-300 rounded px-1.5 py-0.5 font-medium bg-white">⌘K</span>
                </button>

                {/* Search Dropdown */}
                {searchOpen && (
                  <div className="absolute top-full right-0 mt-2 w-96 bg-white rounded-xl border border-slate-200 shadow-2xl overflow-hidden z-50">
                    <div className="p-3 border-b border-slate-100">
                      <div className="relative">
                        <Search size={16} className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400" />
                        <input ref={searchInputRef} type="text" value={searchQuery} onChange={e => setSearchQuery(e.target.value)}
                          placeholder="Search by GSTIN or legal name..."
                          className="w-full pl-9 pr-4 py-2 bg-slate-50 border border-slate-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500/20 focus:border-indigo-300" />
                      </div>
                    </div>
                    <div className="max-h-64 overflow-y-auto">
                      {searchLoading ? (
                        <div className="p-4 flex items-center gap-2 text-sm text-slate-500">
                          <RefreshCw size={14} className="animate-spin" /> Searching...
                        </div>
                      ) : searchResults.length > 0 ? (
                        searchResults.map((r, i) => (
                          <button key={i} onClick={() => handleSearchSelect(r.gstin)}
                            className="w-full text-left px-4 py-3 hover:bg-indigo-50 transition-colors border-b border-slate-50 flex items-center gap-3">
                            <div className={`w-2 h-2 rounded-full ${r.status === 'Suspended' ? 'bg-rose-500' : 'bg-emerald-500'}`} />
                            <div className="flex-1 min-w-0">
                              <p className="text-sm font-mono font-medium text-slate-900 truncate">{r.gstin}</p>
                              <p className="text-xs text-slate-500 truncate">{r.legal_name}</p>
                            </div>
                            <span className={`text-xs px-2 py-0.5 rounded-full font-semibold ${r.status === 'Suspended' ? 'bg-rose-100 text-rose-700' : 'bg-emerald-100 text-emerald-700'}`}>
                              {r.status}
                            </span>
                          </button>
                        ))
                      ) : searchQuery.length >= 2 ? (
                        <div className="p-4 text-center text-sm text-slate-400">No matches found</div>
                      ) : (
                        <div className="p-4 text-center text-sm text-slate-400">Type at least 2 characters to search</div>
                      )}
                    </div>
                  </div>
                )}
              </div>
            </div>
          </header>

          {/* Scrollable Content */}
          <div className="flex-1 overflow-y-auto p-8">
            <div className="max-w-[1600px] mx-auto">
              <Routes>
                <Route path="/" element={<DashboardPage />} />
                <Route path="/reconciliation" element={<ReconciliationPage />} />
                <Route path="/graph" element={<GraphPage />} />
                <Route path="/fraud" element={<FraudPage />} />
                <Route path="/anomalies" element={<AnomalyPage />} />
                <Route path="/alerts" element={<AlertsPage />} />
                <Route path="/query" element={<QueryPage />} />
              </Routes>
            </div>
          </div>

          {/* Status Footer */}
          <footer className="h-7 bg-white border-t border-slate-200 flex items-center justify-between px-6 text-xs text-slate-500 flex-shrink-0">
            <div className="flex items-center gap-4">
              <div className="flex items-center gap-1.5">
                <span className={`w-2 h-2 rounded-full ${statusColor} ${backendStatus === 'online' ? '' : 'animate-pulse'}`} />
                <span>{statusLabel}</span>
              </div>
              <span className="text-slate-300">|</span>
              <span>FastAPI · Groq LLM · NetworkX</span>
            </div>
            <div className="flex items-center gap-4">
              <span>TaxGraph AI v2.0</span>
              <span className="text-slate-300">|</span>
              <span className="flex items-center gap-1"><History size={11} /> {new Date().toLocaleTimeString()}</span>
            </div>
          </footer>
        </main>

        {/* UPLOAD MODAL */}
        {isModalOpen && (
          <div className="fixed inset-0 bg-slate-900/50 backdrop-blur-sm z-50 flex items-center justify-center p-4">
            <div className="bg-white rounded-2xl shadow-xl w-full max-w-md overflow-hidden">
              <div className="p-5 border-b border-slate-100 flex justify-between items-center">
                <h3 className="font-bold text-slate-900">Upload Forensic Data</h3>
                <button onClick={() => setIsModalOpen(false)} className="text-slate-400 hover:text-slate-600">✕</button>
              </div>

              <form onSubmit={handleUpload} className="p-6 space-y-4">
                {[
                  { name: 'taxpayers', label: 'Taxpayer Registry (CSV)' },
                  { name: 'gstr1', label: 'GSTR-1 Invoices (CSV)' },
                  { name: 'gstr2b', label: 'GSTR-2B Invoices (CSV)' },
                  { name: 'gstr3b', label: 'GSTR-3B Summary (CSV)' },
                  { name: 'fraud_labels', label: 'Fraud Labels (CSV)' },
                ].map(field => (
                  <div key={field.name}>
                    <label className="block text-sm font-medium text-slate-700 mb-1">{field.label}</label>
                    <input type="file" name={field.name} accept=".csv" required
                      className="block w-full text-sm text-slate-500 file:mr-4 file:py-2 file:px-4 file:rounded-full file:border-0 file:text-sm file:font-semibold file:bg-indigo-50 file:text-indigo-700 hover:file:bg-indigo-100 transition-colors" />
                  </div>
                ))}
                <div className="pt-4">
                  <button type="submit" disabled={isUploading}
                    className="w-full bg-indigo-600 text-white font-bold py-2.5 rounded-xl hover:bg-indigo-700 transition-colors flex justify-center items-center disabled:opacity-50">
                    {isUploading ? <RefreshCw className="animate-spin mr-2" size={18} /> : null}
                    {isUploading ? "Processing Graph Geometry..." : "Run AI Analysis"}
                  </button>
                </div>
              </form>
            </div>
          </div>
        )}

        {/* Toast Container */}
        <ToastContainer toasts={toasts} removeToast={removeToast} />
      </div>
    </ToastContext.Provider>
  );
}

export default function App() {
  return (
    <BrowserRouter>
      <AppLayout />
    </BrowserRouter>
  );
}