import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { LayoutDashboard, TrendingUp, AlertTriangle, Package2, Landmark, BarChart3, Activity, Sparkles } from 'lucide-react';
import { StatsCard } from '../components/ui/StatsCard';
import { MovementTrendsChart } from '../components/ui/MovementTrendsChart';
import { useDashboardSummary, useAlerts, useDashboardMovements } from '../hooks/useDashboard';
import { useWarehouses } from '../hooks/useWarehouses';
import { cn } from '../lib/utils';
import { asArray } from '../lib/apiResponse';
import { motion } from 'framer-motion';
import { ErrorFallback } from '../components/ui/ErrorFallback';
import { ErrorBoundary } from 'react-error-boundary';

const Dashboard = () => {
  const [trendDays, setTrendDays] = useState(7);
  const [selectedWarehouseId, setSelectedWarehouseId] = useState<number | undefined>(undefined);
  const { data: summary, isLoading: summaryLoading } = useDashboardSummary(selectedWarehouseId);
  const { data: alerts, isLoading: alertsLoading } = useAlerts();
  const { data: movements, isLoading: movementsLoading } = useDashboardMovements(trendDays, selectedWarehouseId);
  const { data: warehouses } = useWarehouses();
  const warehouseList = asArray<{ warehouse_id: number; warehouse_name: string }>(warehouses);
  const alertList = asArray(alerts);
  const navigate = useNavigate();

  return (
    <motion.div 
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      className="space-y-10"
    >
      <div className="flex flex-col lg:flex-row lg:items-end justify-between gap-6 relative">
        <div className="absolute -top-10 -left-10 w-64 h-64 bg-brand-primary/10 rounded-full blur-3xl pointer-events-none" />
        <div className="space-y-2 relative z-10">
          <h1 className="text-4xl md:text-5xl font-black text-slate-900 tracking-tighter flex items-center gap-4" style={{ fontFamily: 'Outfit' }}>
            <div className="p-3 bg-white rounded-2xl shadow-sm border border-slate-100">
              <LayoutDashboard className="text-brand-primary w-8 h-8" />
            </div>
            Operational Overview
          </h1>
          <p className="text-slate-500 font-medium tracking-tight text-lg ml-1">Overview of your assets and inventory.</p>
        </div>
        <div className="flex flex-wrap items-center gap-3 relative z-10">
          {/* Warehouse Dropdown */}
          <div className="flex items-center gap-2 bg-white/80 backdrop-blur-md px-4 py-2 rounded-xl border border-slate-200 shadow-sm">
            <span className="text-xs font-bold text-slate-400 uppercase tracking-wider">Facility:</span>
            <select
              value={selectedWarehouseId || ''}
              onChange={(e) => {
                const val = e.target.value;
                setSelectedWarehouseId(val ? Number(val) : undefined);
              }}
              className="bg-transparent border-none text-slate-700 font-bold focus:outline-none focus:ring-0 cursor-pointer text-sm"
              style={{ fontFamily: 'Outfit' }}
            >
              <option value="">All Warehouses</option>
              {warehouseList.map((wh) => (
                <option key={wh.warehouse_id} value={wh.warehouse_id}>
                  {wh.warehouse_name}
                </option>
              ))}
            </select>
          </div>

          <button 
            onClick={() => navigate('/reports')}
            className="btn-secondary flex items-center gap-2 group"
          >
            <Sparkles className="w-4 h-4 text-brand-primary group-hover:animate-pulse" /> Generate Report
          </button>
          <button 
            onClick={() => navigate('/analytics')}
            className="btn-primary flex items-center gap-2 group shadow-[var(--shadow-elevation-2)]"
          >
            <BarChart3 className="w-4 h-4 group-hover:scale-110 transition-transform" /> Advanced Analytics
          </button>
        </div>
      </div>
      
      {/* KPI Section */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 xl:gap-8">
        <StatsCard 
          title="Stock Items" 
          value={summary?.inventory?.total_items || 0} 
          icon={Package2} 
          color="indigo"
          description="Total items in all stores"
          loading={summaryLoading}
        />
        <StatsCard 
          title="Total Asset Value" 
          value={`${summary?.currency || 'KES'} ${(summary?.total_valuation || 0)?.toLocaleString()}`} 
          icon={Landmark} 
          color="emerald"
          description="Total worth of all assets"
          loading={summaryLoading}
        />
        <StatsCard 
          title="Stock Alerts" 
          value={alertList.length} 
          icon={AlertTriangle} 
          color="amber"
          description="Items that need attention"
          loading={alertsLoading}
        />
        <StatsCard 
          title="Store Health" 
          value={summary?.inventory?.total_items === 0 ? "100%" : `${Math.round(((summary?.inventory?.health?.healthy || 0) / (summary?.inventory?.total_items || 1)) * 100)}%`} 
          icon={Activity} 
          color="slate"
          description="Status of your storage"
          loading={summaryLoading}
        />
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
        <div className="lg:col-span-2 glass-panel p-0 overflow-hidden flex flex-col h-[500px]">
           <div className="p-6 border-b border-white/10 flex justify-between items-center bg-white/5">
              <h3 className="font-bold text-white flex items-center gap-3 tracking-tight text-lg" style={{ fontFamily: 'Outfit' }}>
                <div className="p-1.5 bg-brand-primary/20 rounded-lg">
                  <BarChart3 className="w-5 h-5 text-brand-400" />
                </div>
                Stock Activity
              </h3>
              <div className="flex gap-2">
                <span 
                  onClick={() => setTrendDays(7)}
                  className={cn("px-3 py-1 text-white text-xs font-bold rounded-lg cursor-pointer transition-colors", trendDays === 7 ? "bg-brand-primary/80 shadow-lg" : "bg-white/10 hover:bg-white/20")}
                >
                  7D
                </span>
                <span 
                  onClick={() => setTrendDays(30)}
                  className={cn("px-3 py-1 text-white text-xs font-bold rounded-lg cursor-pointer transition-colors", trendDays === 30 ? "bg-brand-primary/80 shadow-lg" : "bg-white/10 hover:bg-white/20")}
                >
                  30D
                </span>
              </div>
           </div>
           <div className="p-6 flex-1 relative">
             <ErrorBoundary FallbackComponent={ErrorFallback}>
               <MovementTrendsChart data={movements || {}} loading={movementsLoading} />
             </ErrorBoundary>
           </div>
        </div>
        
        <div className="glass-card p-0 overflow-hidden flex flex-col h-[500px]">
          <div className="p-6 border-b border-slate-100/50 bg-slate-50/50">
            <h3 className="font-bold text-slate-800 flex items-center gap-3 tracking-tight text-lg" style={{ fontFamily: 'Outfit' }}>
               <div className="p-1.5 bg-indigo-100 rounded-lg">
                 <Activity className="w-5 h-5 text-indigo-600" />
               </div>
               Recent Alerts
            </h3>
          </div>
          <div className="p-6 space-y-5 flex-1 overflow-y-auto custom-scrollbar">
            {alertList.slice(0, 8).map((alert: any) => (
              <div key={alert.id} className="flex gap-4 group p-3 rounded-xl hover:bg-slate-50 transition-colors border border-transparent hover:border-slate-100 cursor-pointer relative overflow-hidden">
                <div className={cn(
                  "w-1.5 rounded-full shadow-inner",
                  alert.severity === 'CRITICAL' ? "bg-rose-500 shadow-rose-500/50" : "bg-amber-500 shadow-amber-500/50"
                )} />
                <div className="flex-1 min-w-0">
                  <p className="text-sm font-bold text-slate-800 truncate group-hover:text-brand-primary transition-colors">{alert.item_name}</p>
                  <p className="text-xs text-slate-500 mt-1 line-clamp-2 leading-relaxed font-medium">{alert.message}</p>
                  <p className="text-[10px] text-slate-400 mt-2.5 font-bold uppercase tracking-widest flex items-center gap-1.5">
                    <span className="w-1.5 h-1.5 rounded-full bg-slate-300 group-hover:bg-brand-primary transition-colors" />
                    {new Date(alert.created_at).toLocaleTimeString()}
                  </p>
                </div>
              </div>
            ))}
            {!alertList.length && !alertsLoading && (
              <div className="h-full flex flex-col items-center justify-center text-slate-400 opacity-50">
                <Activity className="w-12 h-12 mb-3" />
                <p className="font-medium italic text-sm tracking-wide">No recent alerts.</p>
              </div>
            )}
            {alertsLoading && (
              <div className="space-y-4">
                {[1, 2, 3].map(i => (
                  <div key={i} className="flex gap-4 p-3 animate-pulse">
                    <div className="w-1.5 rounded-full bg-slate-200" />
                    <div className="flex-1 space-y-2">
                      <div className="h-4 bg-slate-200 rounded w-1/2" />
                      <div className="h-3 bg-slate-200 rounded w-full" />
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      </div>
    </motion.div>
  );
};

export default Dashboard;
