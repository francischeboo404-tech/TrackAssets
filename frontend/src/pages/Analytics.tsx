import { useState, useRef, useEffect } from 'react';
import {
  TrendingUp,
  Zap,
  Download,
  RefreshCw,
  Package,
  Barcode,
  QrCode,
  LayoutDashboard,
  AlertTriangle,
} from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';
import { StatsCard } from '../components/ui/StatsCard';
import { MovementTrendsChart } from '../components/ui/MovementTrendsChart';
import {
  AssetReportCharts,
  InventoryReportCharts,
  TrackingReportCharts,
} from '../components/reports/ReportChartPanels';
import {
  useAssetsReport,
  useDashboardReport,
  useInventoryReport,
  useTrackingReport,
} from '../hooks/useReportAnalytics';
import { useAnalyticsExport } from '../hooks/useAnalyticsExport';
import { useAuth } from '../context/AuthContext';
import { canAccess } from '../lib/permissions';
import type { UserRole } from '../types';
import { cn } from '../lib/utils';

type TabId = 'overview' | 'assets' | 'inventory' | 'tracking';

const TABS: { id: TabId; label: string; icon: typeof LayoutDashboard; roles: UserRole[] }[] = [
  { id: 'overview', label: 'Overview', icon: LayoutDashboard, roles: ['admin', 'store_manager', 'auditor', 'dept_head', 'staff', 'viewer'] },
  { id: 'assets', label: 'Assets', icon: Barcode, roles: ['admin', 'store_manager', 'auditor', 'dept_head', 'staff', 'viewer'] },
  { id: 'inventory', label: 'Inventory', icon: Package, roles: ['admin', 'store_manager', 'auditor', 'dept_head', 'staff'] },
  { id: 'tracking', label: 'Tracking', icon: QrCode, roles: ['admin', 'store_manager', 'auditor', 'staff', 'dept_head'] },
];

const Analytics = () => {
  const { user } = useAuth();
  const [days, setDays] = useState(30);
  const [activeTab, setActiveTab] = useState<TabId>('overview');
  const [exportOpen, setExportOpen] = useState(false);
  const exportMenuRef = useRef<HTMLDivElement>(null);
  const analyticsExport = useAnalyticsExport();

  const visibleTabs = TABS.filter((t) => canAccess(user?.role, t.roles));

  const dashboard = useDashboardReport(days);
  const assetsReport = useAssetsReport(days, activeTab === 'assets' || activeTab === 'overview');
  const inventoryReport = useInventoryReport(
    days,
    activeTab === 'inventory' || activeTab === 'overview',
  );
  const trackingReport = useTrackingReport(
    days,
    activeTab === 'tracking' || activeTab === 'overview',
  );

  useEffect(() => {
    const onClick = (e: MouseEvent) => {
      if (exportMenuRef.current && !exportMenuRef.current.contains(e.target as Node)) {
        setExportOpen(false);
      }
    };
    document.addEventListener('mousedown', onClick);
    return () => document.removeEventListener('mousedown', onClick);
  }, []);

  const kpis = dashboard.data?.kpis;
  const currency = kpis?.currency ?? 'KES';
  const isLoading = dashboard.isLoading;

  const refetchAll = () => {
    dashboard.refetch();
    assetsReport.refetch();
    inventoryReport.refetch();
    trackingReport.refetch();
  };

  return (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      className="space-y-8 pb-10 max-w-[1600px] mx-auto"
    >
      <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-6">
        <div className="space-y-2">
          <p className="text-[10px] font-black uppercase tracking-widest text-brand-primary">
            Procurement Intelligence
          </p>
          <h1 className="text-4xl font-black text-slate-900 tracking-tighter" style={{ fontFamily: 'Outfit' }}>
            Reporting & Analytics
          </h1>
          <p className="text-slate-500 font-medium max-w-xl">
            All metrics are computed on the server from live ledger data — charts reflect backend truth only.
          </p>
        </div>
        <div className="flex flex-wrap items-center gap-3">
          <select
            value={days}
            onChange={(e) => setDays(Number(e.target.value))}
            className="px-4 py-2.5 bg-white border border-slate-200 rounded-xl text-sm font-bold text-slate-700"
          >
            <option value={7}>Last 7 days</option>
            <option value={30}>Last 30 days</option>
            <option value={90}>Last 90 days</option>
          </select>
          <button
            type="button"
            onClick={refetchAll}
            className="p-3 bg-white border border-slate-200 rounded-xl text-slate-500 hover:text-brand-primary"
            title="Refresh reports"
          >
            <RefreshCw className={cn('w-5 h-5', dashboard.isFetching && 'animate-spin')} />
          </button>
          {canAccess(user?.role, ['admin', 'store_manager']) && (
            <div className="relative" ref={exportMenuRef}>
              <button
                type="button"
                onClick={() => setExportOpen((o) => !o)}
                className="p-3 bg-white border border-slate-200 rounded-xl text-slate-500 hover:text-brand-primary"
              >
                <Download className="w-5 h-5" />
              </button>
              {exportOpen && (
                <div className="absolute right-0 top-full mt-2 w-56 bg-white border rounded-xl shadow-xl z-50">
                  <button
                    type="button"
                    className="w-full text-left px-4 py-3 text-sm hover:bg-slate-50"
                    onClick={() => {
                      analyticsExport.mutate('movement');
                      setExportOpen(false);
                    }}
                  >
                    Export movement CSV
                  </button>
                  <button
                    type="button"
                    className="w-full text-left px-4 py-3 text-sm hover:bg-slate-50 border-t"
                    onClick={() => {
                      analyticsExport.mutate('valuation');
                      setExportOpen(false);
                    }}
                  >
                    Export valuation CSV
                  </button>
                </div>
              )}
            </div>
          )}
        </div>
      </div>

      <div className="flex flex-wrap gap-2 bg-white/80 p-1.5 rounded-2xl border border-slate-200 shadow-sm">
        {visibleTabs.map((tab) => (
          <button
            key={tab.id}
            type="button"
            onClick={() => setActiveTab(tab.id)}
            className={cn(
              'flex items-center gap-2 px-5 py-2.5 text-xs font-black uppercase tracking-widest rounded-xl transition-all',
              activeTab === tab.id
                ? 'bg-slate-900 text-white shadow-lg'
                : 'text-slate-400 hover:text-slate-600',
            )}
          >
            <tab.icon className="w-4 h-4" />
            {tab.label}
          </button>
        ))}
      </div>

      {(dashboard.isError || assetsReport.isError) && (
        <div className="p-4 bg-rose-50 border border-rose-100 rounded-xl text-sm text-rose-700 font-medium">
          Could not load analytics. Check your permissions or try refreshing.
        </div>
      )}

      <AnimatePresence mode="wait">
        <motion.div
          key={activeTab}
          initial={{ opacity: 0, y: 8 }}
          animate={{ opacity: 1, y: 0 }}
          exit={{ opacity: 0 }}
          className="space-y-8"
        >
          {activeTab === 'overview' && (
            <>
              <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-4 gap-4">
                <StatsCard
                  title="Total Assets"
                  value={String(kpis?.total_assets ?? '—')}
                  icon={Barcode}
                  color="indigo"
                  loading={isLoading}
                />
                <StatsCard
                  title="Inventory Units"
                  value={String(kpis?.total_inventory_units ?? '—')}
                  icon={Package}
                  color="emerald"
                  loading={isLoading}
                />
                <StatsCard
                  title="Utilization"
                  value={`${kpis?.utilization_rate ?? 0}%`}
                  icon={TrendingUp}
                  color="amber"
                  description="In-use / active pool"
                  loading={isLoading}
                />
                <StatsCard
                  title="Compliance"
                  value={`${kpis?.compliance_score ?? 0}%`}
                  icon={Zap}
                  color="indigo"
                  loading={isLoading}
                />
              </div>

              <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
                <div className="lg:col-span-2 enterprise-card p-6 bg-white shadow-xl">
                  <h3 className="font-bold text-slate-900 mb-4">Stock Movement Trends</h3>
                  <MovementTrendsChart
                    data={dashboard.data?.movement_trends ?? {}}
                    loading={isLoading}
                  />
                </div>
                <div className="enterprise-card p-6 bg-white shadow-xl space-y-4">
                  <h3 className="font-bold text-slate-900 flex items-center gap-2">
                    <AlertTriangle className="w-5 h-5 text-amber-500" />
                    Critical Alerts
                  </h3>
                  {(dashboard.data?.critical_alerts ?? []).length === 0 && !isLoading && (
                    <p className="text-sm text-slate-400">No critical alerts.</p>
                  )}
                  {(dashboard.data?.critical_alerts ?? []).map((a, i) => (
                    <div
                      key={i}
                      className="p-3 rounded-xl bg-slate-50 border border-slate-100 text-sm"
                    >
                      <p className="font-bold text-slate-800">{a.title}</p>
                      <p className="text-slate-500">{a.message}</p>
                    </div>
                  ))}
                  <p className="text-xs text-slate-400 pt-2 border-t">
                    Valuation: {currency}{' '}
                    {(kpis?.total_valuation ?? 0).toLocaleString()}
                  </p>
                </div>
              </div>

              {canAccess(user?.role, ['admin', 'store_manager', 'auditor', 'dept_head', 'staff']) && (
                <AssetReportCharts
                  data={dashboard.data?.assets ?? assetsReport.data}
                  loading={assetsReport.isLoading}
                />
              )}
            </>
          )}

          {activeTab === 'assets' && (
            <>
              <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                <StatsCard
                  title="Total Assets"
                  value={String(assetsReport.data?.total_count ?? '—')}
                  icon={Barcode}
                  color="indigo"
                  loading={assetsReport.isLoading}
                />
                <StatsCard
                  title="Utilization Rate"
                  value={`${assetsReport.data?.utilization_rate ?? 0}%`}
                  icon={TrendingUp}
                  color="emerald"
                  loading={assetsReport.isLoading}
                />
                <StatsCard
                  title="Departments"
                  value={String(assetsReport.data?.by_department?.length ?? '—')}
                  icon={LayoutDashboard}
                  color="amber"
                  loading={assetsReport.isLoading}
                />
              </div>
              <AssetReportCharts data={assetsReport.data} loading={assetsReport.isLoading} />
            </>
          )}

          {activeTab === 'inventory' && (
            <>
              <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
                <StatsCard
                  title="Active SKUs"
                  value={String(inventoryReport.data?.total_skus ?? '—')}
                  icon={Package}
                  color="indigo"
                  loading={inventoryReport.isLoading}
                />
                <StatsCard
                  title="Total Units"
                  value={String(inventoryReport.data?.total_units ?? '—')}
                  icon={Package}
                  color="emerald"
                  loading={inventoryReport.isLoading}
                />
                <StatsCard
                  title="Low Stock"
                  value={String(inventoryReport.data?.low_stock_count ?? '—')}
                  icon={AlertTriangle}
                  color="amber"
                  loading={inventoryReport.isLoading}
                />
                <StatsCard
                  title="Valuation"
                  value={`${inventoryReport.data?.currency ?? currency} ${(inventoryReport.data?.total_valuation ?? 0).toLocaleString()}`}
                  icon={TrendingUp}
                  color="indigo"
                  loading={inventoryReport.isLoading}
                />
              </div>
              <InventoryReportCharts
                data={inventoryReport.data}
                loading={inventoryReport.isLoading}
              />
            </>
          )}

          {activeTab === 'tracking' && (
            <>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <StatsCard
                  title="QR Scans"
                  value={String(trackingReport.data?.total_scans ?? '—')}
                  icon={QrCode}
                  color="indigo"
                  loading={trackingReport.isLoading}
                />
                <StatsCard
                  title="Scan Actions"
                  value={String(trackingReport.data?.scans_by_action?.length ?? '—')}
                  icon={Zap}
                  color="emerald"
                  description="Distinct action types"
                  loading={trackingReport.isLoading}
                />
              </div>
              <TrackingReportCharts
                data={trackingReport.data}
                loading={trackingReport.isLoading}
              />
            </>
          )}
        </motion.div>
      </AnimatePresence>
    </motion.div>
  );
};

export default Analytics;
