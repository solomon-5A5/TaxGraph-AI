import React, { useState, useEffect } from 'react';
import { 
  Network, LayoutDashboard, Receipt, Bell, Settings, Users, Plus, 
  LogOut, Search, HelpCircle, RefreshCw, Calendar, Download, 
  TrendingUp, CheckCircle, AlertTriangle, TrendingDown, Shield, 
  ZoomIn, ZoomOut, Filter, Building2, Store, Landmark, Truck 
} from 'lucide-react';

import NetworkGraph from './NetworkGraph';

// --- REUSABLE COMPONENTS ---
const MetricCard = ({ title, value, icon: Icon, trendStr, isTrendUp, iconBg, iconColor, trendColor, trendBg, progressColor, progressWidth }) => (
  <div className="bg-white rounded-xl p-5 border border-slate-200 shadow-sm hover:shadow-md transition-shadow">
    <div className="flex justify-between items-start mb-4">
      <div className={`p-2 rounded-lg ${iconBg} ${iconColor}`}><Icon size={24} /></div>
      <span className={`flex items-center px-2 py-0.5 rounded-full text-xs font-semibold ${trendColor} ${trendBg}`}>
        {isTrendUp ? <TrendingUp size={14} className="mr-1" /> : <TrendingDown size={14} className="mr-1" />}
        {trendStr}
      </span>
    </div>
    <div>
      <p className="text-slate-500 text-sm font-medium">{title}</p>
      <h3 className="text-slate-900 text-2xl font-bold mt-1">{value}</h3>
    </div>
    <div className="mt-4 h-1 w-full bg-slate-100 rounded-full overflow-hidden">
      <div className={`h-full rounded-full ${progressColor}`} style={{ width: progressWidth }}></div>
    </div>
  </div>
);

const AlertItem = ({ type, time, title, message }) => {
  const styles = {
    Critical: "bg-rose-100 text-rose-700 border-rose-200",
    Warning: "bg-orange-100 text-orange-700 border-orange-200",
    Info: "bg-slate-100 text-slate-600 border-slate-200"
  };
  return (
    <div className="p-4 border-b border-slate-50 hover:bg-slate-50 transition-colors cursor-pointer group">
      <div className="flex justify-between items-start mb-1">
        <span className={`text-[10px] font-bold px-2 py-0.5 rounded border uppercase tracking-wide ${styles[type]}`}>{type}</span>
        <span className="text-xs text-slate-400">{time}</span>
      </div>
      <h4 className="text-sm font-semibold text-slate-800 mb-1 group-hover:text-indigo-600 transition-colors">{title}</h4>
      <p className="text-xs text-slate-500 leading-relaxed">{message}</p>
    </div>
  );
};

// --- MAIN APPLICATION ---
export default function App() {
  // 1. Setup React State to hold our API data
  const [graphData, setGraphData] = useState({ nodes: [], links: [] });
  const [isLoading, setIsLoading] = useState(true);

  // 2. Fetch the data from FastAPI when the component loads
  useEffect(() => {
    fetch('http://127.0.0.1:8000/api/graph-data')
      .then(res => res.json())
      .then(data => {
        setGraphData(data);
        setIsLoading(false);
      })
      .catch(err => {
        console.error("Error fetching graph data:", err);
        setIsLoading(false);
      });
  }, []);

  return (
    <div className="bg-slate-50 text-slate-900 overflow-hidden h-screen flex font-sans">
      
      {/* SIDEBAR */}
      <aside className="w-64 bg-white border-r border-slate-200 flex flex-col h-full flex-shrink-0 z-20 shadow-sm">
        <div className="p-6 flex items-center gap-3">
          <div className="bg-gradient-to-br from-indigo-600 to-indigo-800 rounded-lg w-8 h-8 flex items-center justify-center text-white shadow-lg shadow-indigo-600/30">
            <Network size={20} />
          </div>
          <div>
            <h1 className="text-slate-900 font-semibold text-sm leading-tight">GSTGraph AI</h1>
            <p className="text-slate-500 text-xs font-normal">Enterprise</p>
          </div>
        </div>
        
        <div className="px-4 flex flex-col gap-1 mt-2">
          <div className="mb-4">
            <p className="px-4 text-xs font-semibold text-slate-400 uppercase tracking-wider mb-2">Platform</p>
            <a className="flex items-center gap-3 px-4 py-2.5 rounded-full bg-slate-100 text-indigo-600 font-medium transition-colors" href="#"><LayoutDashboard size={20} /> <span className="text-sm">Dashboard</span></a>
            <a className="flex items-center gap-3 px-4 py-2.5 rounded-full text-slate-600 hover:bg-slate-50 hover:text-slate-900 transition-colors" href="#"><Receipt size={20} /> <span className="text-sm">Invoices</span></a>
            <a className="flex items-center gap-3 px-4 py-2.5 rounded-full text-slate-600 hover:bg-slate-50 hover:text-slate-900 transition-colors" href="#"><Network size={20} /> <span className="text-sm">Graph Analysis</span></a>
            <a className="flex items-center gap-3 px-4 py-2.5 rounded-full text-slate-600 hover:bg-slate-50 hover:text-slate-900 transition-colors" href="#"><Bell size={20} /> <span className="text-sm flex-1">Alerts</span><span className="bg-rose-100 text-rose-600 text-xs font-bold px-1.5 py-0.5 rounded-md">3</span></a>
          </div>
        </div>
        
        <div className="mt-auto p-4 border-t border-slate-100">
          <button className="w-full bg-indigo-600 hover:bg-indigo-700 text-white text-sm font-semibold py-2.5 rounded-full shadow-lg shadow-indigo-600/25 transition-all flex items-center justify-center gap-2">
            <Plus size={18} /> New Analysis
          </button>
        </div>
      </aside>

      {/* MAIN CONTENT */}
      <main className="flex-1 flex flex-col min-w-0 overflow-hidden bg-slate-50">
        
        {/* Header */}
        <header className="h-16 bg-white/80 backdrop-blur-md border-b border-slate-200 flex items-center justify-between px-8 sticky top-0 z-10">
          <h2 className="text-slate-800 text-lg font-semibold tracking-tight">Dashboard Overview</h2>
          <div className="flex items-center gap-4">
            <div className="relative group">
              <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none"><Search size={18} className="text-slate-400" /></div>
              <input type="text" placeholder="Search invoices..." className="block w-64 pl-10 pr-12 py-1.5 border-none rounded-lg bg-slate-100 text-slate-900 placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-indigo-600/20 focus:bg-white transition-all text-sm" />
              <div className="absolute inset-y-0 right-0 pr-3 flex items-center pointer-events-none"><span className="text-slate-400 text-xs border border-slate-300 rounded px-1.5 py-0.5 font-medium bg-white">⌘K</span></div>
            </div>
          </div>
        </header>

        {/* Scrollable Content */}
        <div className="flex-1 overflow-y-auto p-8">
          <div className="max-w-[1600px] mx-auto space-y-6">
            
            {/* Date Filter & Metrics */}
            <div className="flex justify-between items-center mb-2">
              <div className="flex items-center gap-2 text-sm text-slate-500">
                <span>Last updated: just now</span>
                {isLoading ? <RefreshCw size={14} className="animate-spin text-indigo-600" /> : <RefreshCw size={14} />}
              </div>
              <div className="flex gap-2">
                <button className="flex items-center gap-2 px-3 py-1.5 bg-white border border-slate-200 rounded-lg text-sm font-medium text-slate-600 shadow-sm"><Calendar size={16} /> This Month</button>
                <button className="flex items-center gap-2 px-3 py-1.5 bg-white border border-slate-200 rounded-lg text-sm font-medium text-slate-600 shadow-sm"><Download size={16} /> Export</button>
              </div>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-4 gap-4">
              <MetricCard title="Total Invoices" value={graphData.links.length || "0"} icon={Receipt} trendStr="12.5%" isTrendUp={true} iconBg="bg-indigo-50" iconColor="text-indigo-600" trendColor="text-emerald-600" trendBg="bg-emerald-50" progressColor="bg-indigo-600" progressWidth="70%" />
              <MetricCard title="Active Taxpayers" value={graphData.nodes.length || "0"} icon={Building2} trendStr="5.2%" isTrendUp={true} iconBg="bg-emerald-50" iconColor="text-emerald-600" trendColor="text-emerald-600" trendBg="bg-emerald-50" progressColor="bg-emerald-500" progressWidth="88%" />
              <MetricCard title="Mismatched" value="1,250" icon={AlertTriangle} trendStr="2.1%" isTrendUp={false} iconBg="bg-orange-50" iconColor="text-orange-500" trendColor="text-emerald-600" trendBg="bg-emerald-50" progressColor="bg-orange-400" progressWidth="15%" />
              <MetricCard title="Fraud Flags" value="4" icon={Shield} trendStr="15.3%" isTrendUp={true} iconBg="bg-rose-50" iconColor="text-rose-500" trendColor="text-rose-600" trendBg="bg-rose-50" progressColor="bg-rose-500" progressWidth="8%" />
            </div>

            {/* Main Grid Layout */}
            <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 h-[600px]">
              
              {/* GRAPH ANALYSIS CANVAS */}
              <div className="lg:col-span-2 bg-white rounded-xl border border-slate-200 shadow-sm flex flex-col overflow-hidden relative group">
                <div className="p-5 border-b border-slate-100 flex justify-between items-center z-10 bg-white">
                  <div>
                    <h3 className="font-semibold text-slate-900">Network Graph Analysis</h3>
                    <p className="text-xs text-slate-500 mt-1">Visualizing entity relationships and circular trading patterns</p>
                  </div>
                  <div className="flex gap-2">
                    <button className="p-1.5 rounded-md text-slate-400 hover:text-slate-600 hover:bg-slate-50 border border-slate-200"><ZoomIn size={18} /></button>
                    <button className="p-1.5 rounded-md text-slate-400 hover:text-slate-600 hover:bg-slate-50 border border-slate-200"><ZoomOut size={18} /></button>
                    <button className="p-1.5 rounded-md text-slate-400 hover:text-slate-600 hover:bg-slate-50 border border-slate-200"><Filter size={18} /></button>
                  </div>
                </div>

                <div className="flex-1 w-full h-full relative bg-slate-50" style={{ backgroundImage: 'radial-gradient(#cbd5e1 1px, transparent 1px)', backgroundSize: '24px 24px' }}>
                  
                  {/* Loading State or Real Data */}
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

              {/* Live Alerts Feed */}
              <div className="bg-white rounded-xl border border-slate-200 shadow-sm flex flex-col overflow-hidden">
                <div className="p-5 border-b border-slate-100 flex justify-between items-center bg-white">
                  <h3 className="font-semibold text-slate-900">Live Alerts Feed</h3>
                  <span className="relative flex h-3 w-3"><span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-rose-400 opacity-75"></span><span className="relative inline-flex rounded-full h-3 w-3 bg-rose-500"></span></span>
                </div>
                <div className="flex-1 overflow-y-auto p-0">
                  <AlertItem type="Critical" time="Just Now" title="Circular Trading Detected" message="Algorithm detected a closed-loop recursive invoicing ring. Transactions flagged in red on the graph." />
                  <AlertItem type="Warning" time="15m ago" title="High Risk Counterparty" message="Multiple active taxpayers trading with globally suspended entity." />
                  <AlertItem type="Info" time="1h ago" title="Data Ingestion Complete" message={`Successfully processed ${graphData.links.length} invoices across ${graphData.nodes.length} taxpayers.`} />
                </div>
              </div>

            </div>
          </div>
        </div>
      </main>
    </div>
  );
}