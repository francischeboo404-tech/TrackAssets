import { useState, useEffect } from 'react';
import { useSearchParams } from 'react-router-dom';
import { Barcode, Search, Calendar, MapPin, Tag, Activity, ArrowRight, Settings, QrCode, ArrowRightLeft } from 'lucide-react';
import { useAssets } from '../hooks/useAssets';
import { AssetLifecycleActions } from '../components/ui/AssetLifecycleActions';
import { canCreateAsset, canEditAsset, canRequestTransfer } from '../lib/permissions';
import { cn } from '../lib/utils';
import { AssetModal } from '../components/ui/AssetModal';
import { AssetQRCode } from '../components/ui/AssetQRCode';
import { Modal } from '../components/ui/Modal';
import { TransferRequestModal } from '../components/ui/TransferRequestModal';
import { useAuth } from '../context/AuthContext';
import { motion, AnimatePresence } from 'framer-motion';

const STATUS_THEMES = {
  requested: 'bg-sky-50 text-sky-700 border-sky-200/50',
  approved: 'bg-indigo-50 text-indigo-700 border-indigo-200/50',
  rejected: 'bg-rose-50 text-rose-700 border-rose-200/50',
  in_use: 'bg-emerald-50 text-emerald-700 border-emerald-200/50',
  maintenance: 'bg-amber-50 text-amber-700 border-amber-200/50',
  disposed: 'bg-slate-50 text-slate-600 border-slate-200/50',
};

const Assets = () => {
  const [searchParams] = useSearchParams();
  const [search, setSearch] = useState('');
  const [statusFilter, setStatusFilter] = useState('');
  const [page, setPage] = useState(1);
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [selectedAsset, setSelectedAsset] = useState<any>(null);
  const [selectedAssetForQR, setSelectedAssetForQR] = useState<any>(null);
  const [selectedAssetForTransfer, setSelectedAssetForTransfer] = useState<any>(null);

  useEffect(() => {
    const q = searchParams.get('q');
    if (q) setSearch(q);
  }, [searchParams]);
  
  const { data, isLoading } = useAssets({ 
    search: search || undefined, 
    status: statusFilter || undefined,
    page 
  });
  
  const assets = (data as any)?.assets || [];
  const pagination = (data as any)?.pagination;
  const { user } = useAuth();

  const handleEdit = (asset: any) => {
    setSelectedAsset(asset);
    setIsModalOpen(true);
  };

  const handleCloseModal = () => {
    setIsModalOpen(false);
    setSelectedAsset(null);
  };

  const getStatusLabel = (status: string) => {
    const labels: Record<string, string> = {
      requested: 'Requested',
      approved: 'Approved',
      rejected: 'Rejected',
      in_use: 'In Use',
      maintenance: 'Maintenance',
      disposed: 'Disposed',
    };
    return labels[status] || status;
  };

  return (
    <motion.div 
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      className="space-y-8 pb-10"
    >
      <div className="flex flex-col md:flex-row md:items-end justify-between gap-6 relative">
        <div className="absolute top-0 right-1/4 w-96 h-96 bg-brand-primary/5 rounded-full blur-3xl pointer-events-none" />
        <div className="space-y-2 relative z-10">
          <h1 className="text-4xl font-black text-slate-900 tracking-tighter flex items-center gap-4" style={{ fontFamily: 'Outfit' }}>
            <div className="p-3 bg-white rounded-2xl shadow-sm border border-slate-100">
              <Barcode className="text-brand-primary w-8 h-8" />
            </div>
            Assets
          </h1>
          <p className="text-slate-500 font-medium tracking-tight text-lg ml-1">Manage your fixed assets.</p>
        </div>
        <div className="flex gap-3 relative z-10">
          {canCreateAsset(user?.role) && (
            <button 
              onClick={() => setIsModalOpen(true)}
              className="btn-primary flex items-center gap-2 group shadow-[var(--shadow-elevation-2)]"
              aria-label="Register New Asset"
            >
              <Settings className="w-4 h-4 group-hover:rotate-90 transition-transform duration-500" /> Add Asset
            </button>
          )}
        </div>
      </div>

      <div className="flex flex-col sm:flex-row gap-4 items-center justify-between glass-panel p-2 rounded-2xl border-slate-200/50 bg-white/40">
        <div className="relative w-full sm:max-w-md group">
          <Search className="absolute left-4 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400 group-focus-within:text-brand-primary transition-colors duration-300" />
          <input 
            type="text" 
            placeholder="Search by serial, name, or location..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="w-full bg-white border border-transparent rounded-xl py-2.5 pl-11 pr-4 text-sm focus:ring-4 focus:ring-brand-primary/10 focus:border-brand-primary/20 transition-all duration-300 outline-none shadow-sm placeholder:text-slate-400"
          />
        </div>
        <div className="flex items-center gap-1.5 overflow-x-auto w-full sm:w-auto pb-2 sm:pb-0 hide-scrollbar px-2">
          <button 
            onClick={() => { setStatusFilter(''); setPage(1); }}
            className={cn(
              "px-4 py-2 rounded-xl text-[11px] font-bold transition-all whitespace-nowrap shadow-sm border",
              !statusFilter ? "bg-slate-800 text-white border-slate-800" : "bg-white text-slate-500 border-slate-200/60 hover:border-slate-300 hover:text-slate-800"
            )}
          >
            All Assets
          </button>
          {Object.keys(STATUS_THEMES).map(status => (
            <button 
              key={status} 
              onClick={() => { setStatusFilter(status); setPage(1); }}
              className={cn(
                "px-4 py-2 rounded-xl text-[11px] font-bold transition-all whitespace-nowrap shadow-sm border",
                statusFilter === status ? "bg-brand-primary text-white border-brand-primary" : "bg-white text-slate-500 border-slate-200/60 hover:border-slate-300 hover:text-brand-primary"
              )}
            >
              {getStatusLabel(status)}
            </button>
          ))}
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-6">
        {isLoading ? (
          [1, 2, 3, 4, 5, 6].map(i => (
            <div key={i} className="glass-card h-64 animate-pulse bg-slate-50/50" />
          ))
        ) : assets?.length === 0 ? (
          <div className="col-span-full py-20 flex flex-col items-center justify-center text-slate-400">
            <Barcode className="w-16 h-16 mb-4 opacity-20" />
            <h3 className="text-xl font-bold text-slate-600">No assets found</h3>
            <p className="mt-2 text-sm">Try adjusting your filters or search term.</p>
          </div>
        ) : (
          <AnimatePresence>
            {assets?.map((asset: any, index: number) => (
              <motion.div 
                initial={{ opacity: 0, scale: 0.95, y: 10 }}
                animate={{ opacity: 1, scale: 1, y: 0 }}
                transition={{ duration: 0.3, delay: index * 0.05 }}
                key={asset.id} 
                className="glass-card group hover:-translate-y-1.5 transition-all duration-300 relative overflow-hidden"
              >
                {/* Highlight line on top */}
                <div className="absolute top-0 left-0 w-full h-1 bg-gradient-to-r from-transparent via-brand-primary/50 to-transparent opacity-0 group-hover:opacity-100 transition-opacity duration-500" />
                
                <div className="p-6 flex flex-col h-full">
                  <div className="flex justify-between items-start mb-6">
                    <div className="space-y-1.5 flex-1 min-w-0 pr-4">
                      <h3 className="font-extrabold text-slate-800 text-[17px] group-hover:text-brand-primary transition-colors uppercase tracking-tight truncate leading-tight">{asset.name}</h3>
                      <p className="text-[10px] font-bold text-slate-400 uppercase tracking-[0.2em]">{asset.asset_code || asset.serial_number || 'NO CODE'}</p>
                    </div>
                    <div className={cn(
                      "px-2.5 py-1 rounded-md text-[10px] font-bold border uppercase tracking-widest whitespace-nowrap shadow-sm",
                      STATUS_THEMES[asset.status as keyof typeof STATUS_THEMES] || STATUS_THEMES.requested
                    )}>
                      {getStatusLabel(asset.status)}
                    </div>
                  </div>

                  <div className="grid grid-cols-2 gap-y-4 gap-x-2 pt-4 border-t border-slate-100/60 mb-6 flex-1">
                    <div className="flex items-center gap-2.5 text-slate-600">
                      <div className="w-6 h-6 rounded-md bg-slate-100 flex items-center justify-center">
                        <MapPin className="w-3.5 h-3.5 text-slate-500" />
                      </div>
                      <span className="text-[13px] font-semibold truncate" title={asset.location}>
                        {asset.location || 'Unassigned'}
                      </span>
                    </div>
                    <div className="flex items-center gap-2.5 text-slate-600">
                      <div className="w-6 h-6 rounded-md bg-slate-100 flex items-center justify-center">
                        <Tag className="w-3.5 h-3.5 text-slate-500" />
                      </div>
                      <span className="text-[13px] font-medium truncate">{asset.department_name || 'Global'}</span>
                    </div>
                    <div className="flex items-center gap-2.5 text-slate-600">
                      <div className="w-6 h-6 rounded-md bg-slate-100 flex items-center justify-center">
                        <Calendar className="w-3.5 h-3.5 text-slate-500" />
                      </div>
                      <span className="text-[13px] font-medium">{asset.purchase_date ? new Date(asset.purchase_date).toLocaleDateString() : 'N/A'}</span>
                    </div>
                    <div className="flex items-center gap-2.5 text-slate-800">
                      <div className="w-6 h-6 rounded-md bg-brand-50 flex items-center justify-center">
                        <Activity className="w-3.5 h-3.5 text-brand-primary" />
                      </div>
                      <span className="text-[13px] font-bold">KES {asset.current_value?.toLocaleString(undefined, { maximumFractionDigits: 0 })}</span>
                    </div>
                  </div>

                  <div className="pt-3 border-t border-slate-100/60">
                    <AssetLifecycleActions
                      assetId={asset.id}
                      currentStatus={asset.status}
                      compact
                    />
                  </div>

                  <div className="pt-4 border-t border-slate-100/60 flex items-center justify-between mt-auto">
                    <div className="flex -space-x-2">
                      <div className="w-7 h-7 rounded-full border-2 border-white bg-slate-200 shadow-sm" />
                      <div className="w-7 h-7 rounded-full border-2 border-white bg-indigo-50 flex items-center justify-center text-[9px] font-bold text-brand-primary shadow-sm">+2</div>
                    </div>
                    <div className="flex items-center gap-2">
                      <button 
                        onClick={() => setSelectedAssetForQR(asset)}
                        className="w-8 h-8 flex items-center justify-center hover:bg-slate-100 text-slate-400 hover:text-brand-primary rounded-lg transition-colors group/qr border border-transparent hover:border-slate-200"
                        title="Generate QR Tag"
                      >
                        <QrCode className="w-4 h-4 group-hover/qr:scale-110 transition-transform" />
                      </button>
                      {canRequestTransfer(user?.role) && (
                        <button 
                          onClick={() => setSelectedAssetForTransfer(asset)}
                          className="w-8 h-8 flex items-center justify-center hover:bg-slate-100 text-slate-400 hover:text-brand-primary rounded-lg transition-colors group/transfer border border-transparent hover:border-slate-200"
                          title="Request Transfer"
                        >
                          <ArrowRightLeft className="w-4 h-4 group-hover/transfer:scale-110 transition-transform" />
                        </button>
                      )}
                      <button 
                        onClick={() => handleEdit(asset)}
                        className="text-[11px] font-bold text-brand-primary hover:text-brand-700 bg-brand-50 hover:bg-brand-100 px-3 py-1.5 rounded-lg transition-colors flex items-center gap-1 group/btn"
                      >
                        {canEditAsset(user?.role) ? 'Edit' : 'View'} Details <ArrowRight className="w-3 h-3 group-hover/btn:translate-x-0.5 transition-transform" />
                      </button>
                    </div>
                  </div>
                </div>
              </motion.div>
            ))}
          </AnimatePresence>
        )}
      </div>

      {pagination && pagination.pages > 1 && (
        <div className="flex justify-center items-center gap-4 pt-4">
          <button 
            disabled={!pagination.has_prev}
            onClick={() => setPage(p => p - 1)}
            className="btn-secondary px-5 py-2.5 disabled:opacity-50"
          >
            Previous
          </button>
          <span className="text-sm font-bold text-slate-600 bg-white px-4 py-2.5 rounded-xl border border-slate-200 shadow-sm">
            Page {pagination.page} of {pagination.pages}
          </span>
          <button 
            disabled={!pagination.has_next}
            onClick={() => setPage(p => p + 1)}
            className="btn-secondary px-5 py-2.5 disabled:opacity-50"
          >
            Next
          </button>
        </div>
      )}

      <AssetModal 
        isOpen={isModalOpen} 
        onClose={handleCloseModal} 
        asset={selectedAsset}
      />

      <Modal 
        isOpen={!!selectedAssetForQR} 
        onClose={() => setSelectedAssetForQR(null)}
        title="Asset Identification Tag"
        size="sm"
      >
        {selectedAssetForQR && (
          <AssetQRCode 
            entityType="asset"
            entityId={selectedAssetForQR.id}
            organisationId={user?.organisation_id || 0}
            label={selectedAssetForQR.name}
            code={selectedAssetForQR.asset_code}
          />
        )}
      </Modal>
      <TransferRequestModal
        isOpen={!!selectedAssetForTransfer}
        onClose={() => setSelectedAssetForTransfer(null)}
        asset={selectedAssetForTransfer}
      />
    </motion.div>
  );
};

export default Assets;
