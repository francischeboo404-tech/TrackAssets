import { useState } from 'react';
import { Warehouse as WarehouseIcon, Box, ArrowRightLeft, Thermometer, Percent, Info, ArrowRight, Edit2, Trash2, Loader2, Save, Globe2, Building2, Users, ShoppingCart, PackageOpen, BadgeCheck, Star } from 'lucide-react';
import { useWarehouses, useDeleteWarehouse, useWarehouseBins, useUpdateBin, useDeleteBin, useOrgWarehouseSummary } from '../hooks/useWarehouses';
import { BinModal } from '../components/ui/BinModal';
import { WarehouseModal } from '../components/ui/WarehouseModal';
import { useToast } from '../context/ToastContext';
import { Can } from '../components/auth/Can';
import { cn } from '../lib/utils';
import { motion, AnimatePresence } from 'framer-motion';
import { useWarehouse } from '../context/WarehouseContext';

const Warehouses = () => {
  const { data: utilization, isLoading } = useWarehouses();
  const { data: orgSummary, isLoading: summaryLoading } = useOrgWarehouseSummary();
  const { activeWarehouse, setActiveWarehouse, warehouses: contextWarehouses } = useWarehouse();
  const { mutate: deleteWarehouse, isPending: isDeleting } = useDeleteWarehouse();
  const [selectedWarehouse, setSelectedWarehouse] = useState<{id: number, name: string} | null>(null);
  const [warehouseToEdit, setWarehouseToEdit] = useState<{id: number, name: string, code: string, address?: string} | null>(null);
  const [isBinModalOpen, setIsBinModalOpen] = useState(false);
  const [isWarehouseModalOpen, setIsWarehouseModalOpen] = useState(false);
  const [expandedBinsWarehouseId, setExpandedBinsWarehouseId] = useState<number | null>(null);
  const { data: binsForSelected = [], isLoading: binsLoading } = useWarehouseBins(expandedBinsWarehouseId || undefined as any);
  const updateBin = useUpdateBin();
  const deleteBinInline = useDeleteBin();
  const [editingBinId, setEditingBinId] = useState<number | null>(null);
  const [editForm, setEditForm] = useState({ code: '', description: '' });
  const { addToast } = useToast();

  return (
    <motion.div 
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      className="space-y-10 pb-10"
    >
      <div className="flex flex-col md:flex-row md:items-end justify-between gap-6 relative">
        <div className="absolute top-0 right-1/4 w-96 h-96 bg-brand-primary/5 rounded-full blur-3xl pointer-events-none" />
        <div className="space-y-2 relative z-10">
          <h1 className="text-4xl font-black text-slate-900 tracking-tighter flex items-center gap-4" style={{ fontFamily: 'Outfit' }}>
            <div className="p-3 bg-white rounded-2xl shadow-sm border border-slate-100">
              <WarehouseIcon className="text-brand-primary w-8 h-8" />
            </div>
            All Warehouses
          </h1>
          <p className="text-slate-500 font-medium tracking-tight text-lg ml-1">
            Enterprise multi-warehouse hub &mdash; manage locations, bins, and switch active context.
          </p>
        </div>
        <div className="flex gap-3 relative z-10">
          <Can roles={['admin']}>
            <button 
              onClick={() => {
                setWarehouseToEdit(null);
                setIsWarehouseModalOpen(true);
              }}
              className="btn-secondary flex items-center gap-2"
            >
              <WarehouseIcon className="w-4 h-4" /> Add Warehouse
            </button>
          </Can>
          <button 
            onClick={() => addToast('info', 'Global Transfer', 'Transfer orchestration is being optimized for cross-border transit.')}
            className="btn-primary flex items-center gap-2 shadow-[var(--shadow-elevation-2)] group"
          >
            <ArrowRightLeft className="w-4 h-4 group-hover:rotate-180 transition-transform duration-500" /> Global Transfer
          </button>
        </div>
      </div>

      {/* ── Org-Wide KPI Summary ── */}
      {orgSummary && (
        <div className="grid grid-cols-2 md:grid-cols-3 xl:grid-cols-6 gap-4">
          {[
            { label: 'Warehouses', value: orgSummary.total_warehouses, icon: WarehouseIcon, color: 'brand' },
            { label: 'Inventory Value', value: `KES ${(orgSummary.total_inventory_value / 1000).toFixed(0)}K`, icon: PackageOpen, color: 'emerald' },
            { label: 'Total Assets', value: orgSummary.total_assets, icon: Box, color: 'indigo' },
            { label: 'Departments', value: orgSummary.total_departments, icon: Building2, color: 'amber' },
            { label: 'Employees', value: orgSummary.total_employees, icon: Users, color: 'violet' },
            { label: 'Pending PRs', value: orgSummary.pending_purchase_requests, icon: ShoppingCart, color: 'rose' },
          ].map((kpi) => (
            <div key={kpi.label} className="bg-white rounded-2xl border border-slate-200 p-5 flex flex-col gap-3 shadow-sm hover:shadow-md transition-shadow">
              <div className={cn('p-2.5 rounded-xl w-fit', {
                'bg-brand-primary/10': kpi.color === 'brand',
                'bg-emerald-50': kpi.color === 'emerald',
                'bg-indigo-50': kpi.color === 'indigo',
                'bg-amber-50': kpi.color === 'amber',
                'bg-violet-50': kpi.color === 'violet',
                'bg-rose-50': kpi.color === 'rose',
              })}>
                <kpi.icon className={cn('w-5 h-5', {
                  'text-brand-primary': kpi.color === 'brand',
                  'text-emerald-600': kpi.color === 'emerald',
                  'text-indigo-600': kpi.color === 'indigo',
                  'text-amber-600': kpi.color === 'amber',
                  'text-violet-600': kpi.color === 'violet',
                  'text-rose-600': kpi.color === 'rose',
                })} />
              </div>
              <div>
                <p className="text-2xl font-black text-slate-900 tracking-tight" style={{ fontFamily: 'Outfit' }}>{kpi.value}</p>
                <p className="text-xs font-bold text-slate-400 uppercase tracking-widest mt-0.5">{kpi.label}</p>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* ── Per-Warehouse Overview Cards (Hub) ── */}
      {orgSummary && orgSummary.warehouses.length > 0 && (
        <div>
          <h2 className="text-lg font-black text-slate-900 mb-4 tracking-tight" style={{ fontFamily: 'Outfit' }}>Warehouse Overview</h2>
          <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-5">
            {orgSummary.warehouses.map((wh) => {
              const isActive = activeWarehouse?.id === wh.id;
              return (
                <motion.div
                  key={wh.id}
                  initial={{ opacity: 0, y: 16 }}
                  animate={{ opacity: 1, y: 0 }}
                  className={cn(
                    'bg-white rounded-2xl border p-6 flex flex-col gap-4 shadow-sm hover:shadow-md transition-all duration-200',
                    isActive ? 'border-brand-primary/50 ring-2 ring-brand-primary/10' : 'border-slate-200'
                  )}
                >
                  <div className="flex items-start justify-between">
                    <div className="flex items-center gap-3">
                      <div className={cn('p-2.5 rounded-xl', wh.is_main_warehouse ? 'bg-brand-primary/10' : 'bg-amber-50')}>
                        <WarehouseIcon className={cn('w-5 h-5', wh.is_main_warehouse ? 'text-brand-primary' : 'text-amber-600')} />
                      </div>
                      <div>
                        <div className="flex items-center gap-2">
                          <h3 className="font-bold text-slate-900 text-base leading-none">{wh.name}</h3>
                          {wh.is_main_warehouse && <span className="text-[9px] font-black uppercase tracking-wider bg-brand-primary/10 text-brand-primary px-1.5 py-0.5 rounded-md">HQ</span>}
                        </div>
                        <p className="text-[10px] font-mono text-slate-400 mt-1">{wh.code}</p>
                      </div>
                    </div>
                    {isActive && <BadgeCheck className="w-5 h-5 text-brand-primary shrink-0" />}
                  </div>

                  <div className="grid grid-cols-2 gap-3 text-sm">
                    <div className="bg-slate-50 rounded-xl p-3">
                      <p className="text-[10px] font-bold uppercase tracking-wider text-slate-400">Stock Units</p>
                      <p className="text-xl font-black text-slate-900 mt-1">{wh.stock_units.toLocaleString()}</p>
                    </div>
                    <div className="bg-slate-50 rounded-xl p-3">
                      <p className="text-[10px] font-bold uppercase tracking-wider text-slate-400">Assets</p>
                      <p className="text-xl font-black text-slate-900 mt-1">{wh.asset_count}</p>
                    </div>
                    <div className="bg-slate-50 rounded-xl p-3">
                      <p className="text-[10px] font-bold uppercase tracking-wider text-slate-400">Departments</p>
                      <p className="text-xl font-black text-slate-900 mt-1">{wh.department_count}</p>
                    </div>
                    <div className="bg-slate-50 rounded-xl p-3">
                      <p className="text-[10px] font-bold uppercase tracking-wider text-slate-400">Bin Usage</p>
                      <p className="text-xl font-black text-slate-900 mt-1">{wh.utilization_percentage.toFixed(0)}%</p>
                    </div>
                  </div>

                  <button
                    id={`hub-switch-warehouse-${wh.id}`}
                    onClick={() => {
                      const ctx = contextWarehouses.find(c => c.id === wh.id);
                      if (ctx) setActiveWarehouse(isActive ? null : ctx);
                    }}
                    className={cn(
                      'w-full py-2.5 rounded-xl text-sm font-bold transition-all duration-200 border',
                      isActive
                        ? 'bg-brand-primary text-white border-brand-primary hover:bg-brand-700'
                        : 'bg-white border-slate-200 text-slate-700 hover:border-brand-primary/50 hover:text-brand-primary'
                    )}
                  >
                    {isActive ? 'Active — Click to reset' : 'Set as Active Warehouse'}
                  </button>
                </motion.div>
              );
            })}
          </div>
        </div>
      )}

      {/* ── Existing Bin Management Section ── */}
      <div className="grid grid-cols-1 xl:grid-cols-2 gap-8 relative z-10">
        {isLoading ? (
          [1, 2].map(i => <div key={i} className="glass-card h-80 animate-pulse bg-slate-50/50" />)
        ) : (
          <AnimatePresence>
            {utilization?.map((wh: any, idx: number) => {
              const warehouseKey = wh?.warehouse_id ?? wh?.id ?? `${wh?.warehouse_name ?? 'warehouse'}-${idx}`;

              return (
              <motion.div 
                key={warehouseKey} 
                initial={{ opacity: 0, y: 20, scale: 0.95 }}
                animate={{ opacity: 1, y: 0, scale: 1 }}
                transition={{ delay: idx * 0.1, duration: 0.4 }}
                className="glass-card p-0 overflow-hidden group flex flex-col hover:-translate-y-1.5 transition-all duration-300"
              >
                <div className="p-8 bg-slate-900 text-white flex justify-between items-center relative overflow-hidden shadow-md">
                  {/* Background accent */}
                  <div className="absolute inset-0 bg-gradient-to-r from-brand-primary/20 to-transparent opacity-50" />
                  <div className="absolute -top-10 -right-10 w-40 h-40 bg-brand-primary/30 blur-3xl rounded-full" />
                  
                  <div className="flex items-center gap-5 relative z-10">
                    <div className="p-3.5 bg-white/10 rounded-2xl backdrop-blur-md ring-1 ring-white/20 shadow-lg group-hover:scale-105 transition-transform">
                      <WarehouseIcon className="w-6 h-6 text-white drop-shadow-md" />
                    </div>
                    <div>
                      <h3 className="font-extrabold text-[22px] tracking-tight leading-tight" style={{ fontFamily: 'Outfit' }}>{wh.warehouse_name}</h3>
                      <p className="text-[10px] text-slate-300 uppercase tracking-[0.2em] font-bold mt-1">{wh.warehouse_code}</p>
                    </div>
                  </div>
                  <div className="text-right relative z-10">
                    <p className="text-3xl font-black text-white tabular-nums drop-shadow-md">{(wh.utilization_percentage || 0).toFixed(1)}<span className="text-xl text-slate-300">%</span></p>
                    <p className="text-[10px] text-slate-300 uppercase font-bold tracking-[0.15em] mt-1">Utilization</p>
                  </div>
                </div>

                <div className="p-8 flex-1 space-y-8 bg-white/50">
                  <div className="w-full bg-slate-100 h-5 rounded-full overflow-hidden border border-slate-200/50 p-1 shadow-inner relative">
                    <div 
                      className={cn(
                        "h-full rounded-full transition-all duration-1000 ease-out relative overflow-hidden",
                        wh.utilization_percentage > 90 ? "bg-gradient-to-r from-rose-500 to-rose-400 shadow-[0_0_15px_rgba(244,63,94,0.4)]" : 
                        wh.utilization_percentage > 70 ? "bg-gradient-to-r from-amber-500 to-amber-400 shadow-[0_0_15px_rgba(245,158,11,0.4)]" : "bg-gradient-to-r from-brand-primary to-brand-400 shadow-[0_0_15px_rgba(37,99,235,0.4)]"
                      )}
                      style={{ width: `${wh.utilization_percentage || 0}%` }}
                    >
                      <div className="absolute inset-0 bg-white/20 w-full animate-[shimmer_2s_infinite] -skew-x-12" />
                    </div>
                  </div>
   
                  <div className="grid grid-cols-3 gap-6">
                    <div className="bg-slate-50/80 p-5 rounded-2xl border border-slate-100 text-center space-y-2.5 group/stat hover:bg-white hover:shadow-sm transition-all duration-300">
                      <div className="w-8 h-8 mx-auto bg-brand-50 rounded-lg flex items-center justify-center">
                        <Box className="w-4 h-4 text-brand-primary transition-transform group-hover/stat:rotate-12 group-hover/stat:scale-110" />
                      </div>
                      <p className="text-[22px] font-black text-slate-800 tabular-nums leading-none">{wh.total_bins}</p>
                      <p className="text-[10px] font-bold text-slate-400 uppercase tracking-widest">Slots</p>
                    </div>
                    <div className="bg-slate-50/80 p-5 rounded-2xl border border-slate-100 text-center space-y-2.5 group/stat hover:bg-white hover:shadow-sm transition-all duration-300">
                      <div className="w-8 h-8 mx-auto bg-emerald-50 rounded-lg flex items-center justify-center">
                        <Percent className="w-4 h-4 text-emerald-600 transition-transform group-hover/stat:rotate-12 group-hover/stat:scale-110" />
                      </div>
                      <p className="text-[22px] font-black text-slate-800 tabular-nums leading-none">{wh.occupied_bins}</p>
                      <p className="text-[10px] font-bold text-slate-400 uppercase tracking-widest">Active</p>
                    </div>
                    <div className="bg-slate-50/80 p-5 rounded-2xl border border-slate-100 text-center space-y-2.5 group/stat hover:bg-white hover:shadow-sm transition-all duration-300">
                      <div className="w-8 h-8 mx-auto bg-amber-50 rounded-lg flex items-center justify-center">
                        <Thermometer className="w-4 h-4 text-amber-600 transition-transform group-hover/stat:rotate-12 group-hover/stat:scale-110" />
                      </div>
                      <p className="text-[22px] font-black text-slate-800 tabular-nums leading-none">{wh.empty_bins}</p>
                      <p className="text-[10px] font-bold text-slate-400 uppercase tracking-widest">Empty</p>
                    </div>
                  </div>
   
                  <div className="bg-brand-primary/5 rounded-2xl p-5 border border-brand-primary/10 flex items-start gap-4">
                    <Info className="w-5 h-5 text-brand-primary shrink-0 mt-0.5" />
                    <p className="text-[13px] text-slate-600 leading-relaxed font-medium">
                      <span className="text-brand-primary font-bold uppercase text-[10px] block mb-1 tracking-widest">Capacity Intelligence</span>
                      Optimal density is {wh.utilization_percentage > 85 ? 'approaching critical threshold' : 'within recommended parameters'}. Consider zone rotation for efficient picking.
                    </p>
                  </div>
                </div>

                <div className="px-8 py-5 border-t border-slate-100/60 bg-white/50 flex flex-col gap-3 mt-auto">
                   <Can roles={['admin']}>
                     <div className="flex gap-2">
                       <button 
                         onClick={() => {
                          setWarehouseToEdit({ id: wh.warehouse_id ?? wh.id, name: wh.warehouse_name ?? wh.name, code: wh.warehouse_code ?? wh.code, address: wh.address });
                           setIsWarehouseModalOpen(true);
                         }}
                         className="p-2 text-slate-400 hover:text-brand-primary hover:bg-brand-50 rounded-xl transition-colors"
                         title="Edit Warehouse"
                       >
                         <Edit2 className="w-4 h-4" />
                       </button>
                       <button 
                         onClick={() => {
                           if (window.confirm(`Are you sure you want to delete ${wh.warehouse_name}?`)) {
                             deleteWarehouse(wh.warehouse_id ?? wh.id, {
                               onSuccess: () => addToast('success', 'Deleted', 'Warehouse successfully removed.'),
                               onError: () => addToast('error', 'Error', 'Failed to delete warehouse.')
                             });
                           }
                         }}
                         disabled={isDeleting}
                         className="p-2 text-slate-400 hover:text-rose-600 hover:bg-rose-50 rounded-xl transition-colors disabled:opacity-50"
                         title="Delete Warehouse"
                       >
                         <Trash2 className="w-4 h-4" />
                       </button>
                     </div>
                   </Can>
                   <div className="flex items-center justify-between">
                     <Can roles={['admin', 'store_manager']}>
                       <div className="flex gap-2">
                         <button
                           onClick={() => {
                             setSelectedWarehouse({ id: wh.warehouse_id ?? wh.id, name: wh.warehouse_name ?? wh.name });
                             setIsBinModalOpen(true);
                           }}
                           className="text-[11px] font-bold text-brand-primary hover:text-brand-700 bg-brand-50 hover:bg-brand-100 px-4 py-2 rounded-xl transition-colors flex items-center gap-1.5 group/btn uppercase tracking-widest"
                         >
                           Manage Bins <ArrowRight className="w-3.5 h-3.5 group-hover/btn:translate-x-1 transition-transform" />
                         </button>

                         <button
                           onClick={() => setExpandedBinsWarehouseId(expandedBinsWarehouseId === (wh.warehouse_id ?? wh.id) ? null : (wh.warehouse_id ?? wh.id))}
                           className="text-[11px] font-medium text-slate-600 bg-slate-50 px-3 py-2 rounded-xl hover:bg-slate-100 transition-colors"
                         >
                           {expandedBinsWarehouseId === (wh.warehouse_id ?? wh.id) ? 'Hide bins' : 'Show bins'}
                         </button>
                       </div>
                     </Can>
                   </div>
                   {expandedBinsWarehouseId === wh.warehouse_id && (
                     <div className="w-full mt-3 bg-slate-50 p-4 rounded-xl border">
                       <h4 className="font-bold text-sm mb-2">Bins</h4>
                       {binsLoading ? (
                         <div className="text-sm text-slate-500 flex items-center gap-2"><Loader2 className="w-4 h-4 animate-spin"/> Loading...</div>
                       ) : binsForSelected.length === 0 ? (
                         <div className="text-sm text-slate-500">No bins available for this warehouse.</div>
                       ) : (
                         <div className="space-y-2">
                           {binsForSelected.map((b: any) => (
                             <div key={b.id} className="flex items-center justify-between p-3 bg-white rounded-md border">
                               <div>
                                 <div className="font-mono font-bold">{b.code}</div>
                                 <div className="text-xs text-slate-500">{b.description || '—'}</div>
                               </div>
                               <div className="flex items-center gap-2">
                                 <span className="text-xs px-2 py-1 rounded-lg bg-slate-100">{b.status}</span>
                                 <Can roles={['admin', 'store_manager']}>
                                   {editingBinId === b.id ? (
                                     <div className="flex items-center gap-2">
                                       <input className="input-field w-36" value={editForm.code} onChange={e => setEditForm({...editForm, code: e.target.value.toUpperCase()})} />
                                       <input className="input-field w-56" value={editForm.description} onChange={e => setEditForm({...editForm, description: e.target.value})} />
                                       <button className="p-2 bg-emerald-500 text-white rounded" onClick={async () => {
                                         try {
                                           await updateBin.mutateAsync({ warehouseId: wh.warehouse_id ?? wh.id, binId: b.id, data: { code: editForm.code, description: editForm.description } });
                                           setEditingBinId(null);
                                           setEditForm({ code: '', description: '' });
                                         } catch (err) {
                                           // toast handled elsewhere
                                         }
                                       }}><Save className="w-4 h-4"/></button>
                                       <button className="p-2 bg-slate-200 rounded" onClick={() => { setEditingBinId(null); setEditForm({ code: '', description: '' }); }}>Cancel</button>
                                     </div>
                                   ) : (
                                     <div className="flex gap-2">
                                       <button className="p-2 text-slate-500 hover:text-brand-primary" onClick={() => { setEditingBinId(b.id); setEditForm({ code: b.code, description: b.description || '' }); }} title="Edit Bin"><Edit2 className="w-4 h-4"/></button>
                                       <button className="p-2 text-rose-600 hover:bg-rose-50 rounded" onClick={async () => {
                                         if (!window.confirm(`Delete bin ${b.code}?`)) return;
                                           try { await deleteBinInline.mutateAsync({ warehouseId: wh.warehouse_id ?? wh.id, binId: b.id }); } catch (err) {}
                                       }} title="Delete Bin"><Trash2 className="w-4 h-4"/></button>
                                     </div>
                                   )}
                                 </Can>
                               </div>
                             </div>
                           ))}
                         </div>
                       )}
                     </div>
                   )}
                </div>
              </motion.div>
              );
            })}
          </AnimatePresence>
        )}
        
        {!isLoading && utilization?.length === 0 && (
          <div className="col-span-full py-16 flex flex-col items-center justify-center text-center glass-card border-dashed">
            <div className="w-16 h-16 bg-slate-100 rounded-full flex items-center justify-center mb-4">
              <WarehouseIcon className="w-8 h-8 text-slate-400" />
            </div>
            <h3 className="text-xl font-bold text-slate-800 mb-2">No Warehouses Found</h3>
            <p className="text-slate-500 max-w-md mb-6">You haven't added any warehouse facilities yet. Add your first warehouse to start managing bins and inventory locations.</p>
            <Can roles={['admin']}>
              <button 
                onClick={() => {
                  setWarehouseToEdit(null);
                  setIsWarehouseModalOpen(true);
                }}
                className="btn-primary shadow-lg shadow-brand-primary/20"
              >
                Create Warehouse
              </button>
            </Can>
          </div>
        )}
      </div>
      <BinModal 
        isOpen={isBinModalOpen} 
        onClose={() => setIsBinModalOpen(false)} 
        warehouseId={selectedWarehouse?.id || 0}
        warehouseName={selectedWarehouse?.name || ''}
      />
      <WarehouseModal 
        isOpen={isWarehouseModalOpen} 
        onClose={() => {
          setIsWarehouseModalOpen(false);
          setWarehouseToEdit(null);
        }}
        initialData={warehouseToEdit || undefined}
      />
    </motion.div>
  );
};

export default Warehouses;
