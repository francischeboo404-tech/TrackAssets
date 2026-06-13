import { useState, useEffect } from 'react';
import { useSearchParams } from 'react-router-dom';
import { Package, Search, Plus, Minus, MoreVertical, Filter, AlertCircle, QrCode, ArrowUpRight, ArrowRightLeft } from 'lucide-react';
import { useInventory } from '../hooks/useInventory';
import { cn } from '../lib/utils';
import { StockAdjustmentModal } from '../components/ui/StockAdjustmentModal';
import { useToast } from '../context/ToastContext';
import { Can } from '../components/auth/Can';
import { InventoryModal } from '../components/ui/InventoryModal';
import { InventoryEditModal } from '../components/ui/InventoryEditModal';
import { ConfirmDeleteModal } from '../components/ui/ConfirmDeleteModal';
import { useDeleteInventoryItem } from '../hooks/useInventory';
import {
  canAdjustStock,
  canDeleteInventory,
  canEditInventory,
  canRequestTransfer,
} from '../lib/permissions';
import { TransferRequestModal } from '../components/ui/TransferRequestModal';
import { AssetQRCode } from '../components/ui/AssetQRCode';
import { Modal } from '../components/ui/Modal';
import { useAuth } from '../context/AuthContext';
import { motion } from 'framer-motion';

const Inventory = () => {
  const [searchParams] = useSearchParams();
  const [search, setSearch] = useState('');
  const [selectedItem, setSelectedItem] = useState<any>(null);
  const [selectedItemForQR, setSelectedItemForQR] = useState<any>(null);
  const [selectedItemForTransfer, setSelectedItemForTransfer] = useState<any>(null);
  const [isStockModalOpen, setIsStockModalOpen] = useState(false);
  const [isCreateModalOpen, setIsCreateModalOpen] = useState(false);
  const [isTransferModalOpen, setIsTransferModalOpen] = useState(false);
  const [isEditModalOpen, setIsEditModalOpen] = useState(false);
  const [isDeleteModalOpen, setIsDeleteModalOpen] = useState(false);
  const [adjustmentType, setAdjustmentType] = useState<'IN' | 'OUT'>('IN');
  const [page, setPage] = useState(1);

  useEffect(() => {
    const q = searchParams.get('q');
    if (q) setSearch(q);
  }, [searchParams]);
  const { addToast } = useToast();
  const deleteItem = useDeleteInventoryItem();
  
  const { data, isLoading } = useInventory({ search: search || undefined, page });
  const items = (data as any)?.inventory || [];
  const pagination = (data as any)?.pagination;
  const { user } = useAuth();

  const openAdjustment = (item: any, type: 'IN' | 'OUT') => {
    setSelectedItem(item);
    setAdjustmentType(type);
    setIsStockModalOpen(true);
  };

  const openTransfer = (item: any) => {
    setSelectedItemForTransfer(item);
    setIsTransferModalOpen(true);
  };

  const openEdit = (item: any) => {
    setSelectedItem(item);
    setIsEditModalOpen(true);
  };

  const openDelete = (item: any) => {
    setSelectedItem(item);
    setIsDeleteModalOpen(true);
  };

  const handleDeleteConfirm = async () => {
    if (!selectedItem) return;
    try {
      await deleteItem.mutateAsync(selectedItem.id);
      addToast('success', 'Item Deleted', `${selectedItem.name} was removed.`);
      setIsDeleteModalOpen(false);
      setSelectedItem(null);
    } catch (err: any) {
      addToast(
        'error',
        'Delete Failed',
        err.response?.data?.message ||
          err.forbiddenMessage ||
          'Could not delete this item.',
      );
    }
  };



  return (
    <motion.div 
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      className="space-y-8"
    >
      <div className="flex flex-col md:flex-row md:items-end justify-between gap-6 relative">
        <div className="absolute top-0 right-0 w-96 h-96 bg-indigo-500/5 rounded-full blur-3xl pointer-events-none" />
        <div className="space-y-2 relative z-10">
          <h1 className="text-4xl font-black text-slate-900 tracking-tighter flex items-center gap-4" style={{ fontFamily: 'Outfit' }}>
            <div className="p-3 bg-white rounded-2xl shadow-sm border border-slate-100">
              <Package className="text-brand-primary w-8 h-8" />
            </div>
            Inventory
          </h1>
          <p className="text-slate-500 font-medium tracking-tight text-lg ml-1">Manage your consumable stock.</p>
        </div>
        <div className="flex gap-3 relative z-10">
          <button className="btn-secondary flex items-center gap-2 group">
            <Filter className="w-4 h-4 text-slate-400 group-hover:text-brand-primary transition-colors" /> Advanced Filters
          </button>
          <Can roles={['admin', 'store_manager']}>
            <button 
              onClick={() => setIsCreateModalOpen(true)}
              className="btn-primary flex items-center gap-2 shadow-[var(--shadow-elevation-2)] group"
            >
              <Plus className="w-4 h-4 group-hover:rotate-90 transition-transform duration-300" /> Add Item
            </button>
          </Can>
        </div>
      </div>

      <div className="table-container">
        <div className="p-5 border-b border-slate-100/60 bg-white/50 backdrop-blur-md flex flex-col sm:flex-row gap-4 justify-between items-center sticky top-0 z-20">
          <div className="relative w-full sm:max-w-sm group">
            <Search className="absolute left-3.5 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400 group-focus-within:text-brand-primary transition-colors duration-300" />
            <input 
              type="text" 
              placeholder="Search by SKU or item name..."
              value={search}
              onChange={(e) => { setSearch(e.target.value); setPage(1); }}
              className="w-full bg-slate-50 border border-slate-200/60 rounded-xl py-2.5 pl-10 pr-4 text-sm focus:ring-4 focus:ring-brand-primary/10 focus:bg-white focus:border-brand-primary/30 transition-all duration-300 outline-none shadow-inner shadow-slate-100/50"
            />
          </div>
          <div className="flex items-center gap-4 text-[13px] text-slate-500 font-semibold bg-slate-50 px-3 py-1.5 rounded-lg border border-slate-100">
             <span>{pagination ? `Total Assets: ${pagination.total}` : `Showing ${items?.length || 0} items`}</span>
          </div>
        </div>

        <div className="overflow-visible md:overflow-x-auto min-h-[400px]">
          <table className="w-full text-left border-collapse responsive-table">
            <thead>
              <tr className="bg-slate-50/80">
                <th className="table-header w-[40%]">Item Name</th>
                <th className="table-header text-center">Volume</th>
                <th className="table-header text-right">Unit Value</th>
                <th className="table-header pl-4 md:pl-10">Health Status</th>
                <th className="table-header text-right w-[15%]">Quick Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100/60">
              {isLoading ? (
                [1, 2, 3, 4, 5].map(i => (
                  <tr key={i} className="animate-pulse">
                    <td colSpan={5} className="px-6 py-6 h-[72px] bg-slate-50/30" />
                  </tr>
                ))
              ) : items?.length === 0 ? (
                <tr>
                  <td colSpan={5} className="px-6 py-20 text-center text-slate-400">
                    <Package className="w-12 h-12 mx-auto mb-3 opacity-20" />
                    <p className="font-semibold text-lg">No inventory items found</p>
                    <p className="text-sm">Try adjusting your filters or search query.</p>
                  </td>
                </tr>
              ) : (
                items?.map((item: any, index: number) => (
                  <motion.tr 
                    initial={{ opacity: 0, y: 10 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ delay: index * 0.05 }}
                    key={item.id} 
                    className="table-row group relative"
                  >
                    <td className="table-cell py-5" data-label="Item Details">
                      <div className="flex items-center gap-4">
                        <div className="w-10 h-10 rounded-xl bg-slate-100 flex items-center justify-center border border-slate-200/60 shadow-sm group-hover:border-brand-primary/30 transition-colors flex-shrink-0">
                           <Package className="w-5 h-5 text-slate-400 group-hover:text-brand-primary transition-colors" />
                        </div>
                        <div>
                          <p className="font-bold text-slate-900 leading-tight group-hover:text-brand-primary transition-colors tracking-tight text-[15px]">{item.name}</p>
                          <p className="text-[11px] text-slate-400 mt-1 font-mono tracking-[0.1em]">{item.sku || 'N/A'}</p>
                        </div>
                      </div>
                    </td>
                    <td className="table-cell md:text-center" data-label="Volume">
                      <div className="flex flex-col items-start md:items-center justify-center">
                        <span className={cn(
                          "font-mono font-extrabold text-xl tracking-tight leading-none",
                          item.quantity < (item.reorder_level || 10) ? "text-rose-600" : "text-slate-800"
                        )}>
                          {item.quantity}
                        </span>
                        <span className="text-[10px] text-slate-400 mt-1 font-bold uppercase tracking-widest">{item.unit || 'UNITS'}</span>
                      </div>
                    </td>
                    <td className="table-cell md:text-right" data-label="Unit Value">
                       <span className="font-semibold text-slate-600">KES {item.unit_price?.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}</span>
                    </td>
                    <td className="table-cell pl-0 md:pl-10" data-label="Health Status">
                      {item.quantity < (item.reorder_level || 10) ? (
                        <div className="badge badge-danger gap-1.5 shadow-sm">
                           <AlertCircle className="w-3 h-3" /> CRITICAL
                        </div>
                      ) : (
                        <div className="badge badge-success gap-1.5 shadow-sm">
                           <div className="w-1.5 h-1.5 rounded-full bg-emerald-500 animate-pulse" /> OPTIMAL
                        </div>
                      )}
                    </td>
                    <td className="table-cell md:text-right relative" data-label="Quick Actions">
                      <div className="flex items-center justify-end gap-1.5 opacity-100 md:opacity-0 group-hover:opacity-100 transition-all duration-300 md:translate-x-4 group-hover:translate-x-0">
                        {canAdjustStock(user?.role) && (
                          <>
                          <button 
                            onClick={() => openAdjustment(item, 'IN')}
                            className="w-10 h-10 md:w-8 md:h-8 flex items-center justify-center bg-emerald-50 hover:bg-emerald-100 text-emerald-600 rounded-lg transition-colors border border-emerald-100/50 hover:border-emerald-200 hover:shadow-sm"
                            title="Quick Restock"
                          >
                            <ArrowUpRight className="w-4 h-4" />
                          </button>
                          <button 
                            onClick={() => openAdjustment(item, 'OUT')}
                            className="w-10 h-10 md:w-8 md:h-8 flex items-center justify-center bg-rose-50 hover:bg-rose-100 text-rose-600 rounded-lg transition-colors border border-rose-100/50 hover:border-rose-200 hover:shadow-sm"
                            title="Quick Dispatch"
                          >
                            <Minus className="w-4 h-4" />
                          </button>
                          </>
                        )}
                        <div className="w-px h-5 bg-slate-200 mx-1 hidden md:block" />
                        {canRequestTransfer(user?.role) && (
                        <button 
                          onClick={() => openTransfer(item)}
                          className="w-10 h-10 md:w-8 md:h-8 flex items-center justify-center hover:bg-brand-50 text-brand-primary rounded-lg transition-colors"
                          title="Request Transfer"
                        >
                          <ArrowRightLeft className="w-4 h-4" />
                        </button>
                        )}
                        <button 
                          onClick={() => setSelectedItemForQR(item)}
                          className="w-10 h-10 md:w-8 md:h-8 flex items-center justify-center hover:bg-brand-50 text-slate-400 hover:text-brand-primary rounded-lg transition-colors"
                          title="Generate SKU Tag"
                        >
                          <QrCode className="w-4 h-4" />
                        </button>
                        {(canEditInventory(user?.role) || canDeleteInventory(user?.role)) && (
                          <div className="relative group/menu">
                            <button
                              type="button"
                              className="w-10 h-10 md:w-8 md:h-8 flex items-center justify-center hover:bg-slate-100 text-slate-400 rounded-lg transition-colors"
                              aria-label="More actions"
                            >
                              <MoreVertical className="w-4 h-4" />
                            </button>
                            <div className="absolute right-0 top-full mt-1 z-30 hidden group-hover/menu:block min-w-[140px] bg-white border border-slate-200 rounded-xl shadow-lg py-1">
                              {canEditInventory(user?.role) && (
                                <button
                                  type="button"
                                  onClick={() => openEdit(item)}
                                  className="w-full text-left px-3 py-2 text-xs font-semibold text-slate-700 hover:bg-slate-50"
                                >
                                  Edit item
                                </button>
                              )}
                              {canDeleteInventory(user?.role) && (
                                <button
                                  type="button"
                                  onClick={() => openDelete(item)}
                                  className="w-full text-left px-3 py-2 text-xs font-semibold text-rose-600 hover:bg-rose-50"
                                >
                                  Delete item
                                </button>
                              )}
                            </div>
                          </div>
                        )}
                      </div>
                    </td>
                  </motion.tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>

      {pagination && pagination.pages > 1 && (
        <div className="flex justify-center items-center gap-4 pt-4 pb-10">
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

      <StockAdjustmentModal 
        isOpen={isStockModalOpen}
        onClose={() => setIsStockModalOpen(false)}
        item={selectedItem}
        initialType={adjustmentType}
      />

      <InventoryModal
        isOpen={isCreateModalOpen}
        onClose={() => setIsCreateModalOpen(false)}
      />

      <InventoryEditModal
        isOpen={isEditModalOpen}
        onClose={() => {
          setIsEditModalOpen(false);
          setSelectedItem(null);
        }}
        item={selectedItem}
      />

      <ConfirmDeleteModal
        isOpen={isDeleteModalOpen}
        onClose={() => {
          setIsDeleteModalOpen(false);
          setSelectedItem(null);
        }}
        onConfirm={handleDeleteConfirm}
        isLoading={deleteItem.isPending}
        title="Delete inventory item?"
        message={
          selectedItem
            ? `Permanently remove "${selectedItem.name}"? Items with remaining stock cannot be deleted.`
            : ''
        }
      />



      <TransferRequestModal
        isOpen={isTransferModalOpen}
        onClose={() => setIsTransferModalOpen(false)}
        inventoryItem={selectedItemForTransfer}
        itemType="inventory"
      />

      <Modal 
        isOpen={!!selectedItemForQR} 
        onClose={() => setSelectedItemForQR(null)}
        title="Inventory Tracking Tag"
        size="sm"
      >
        {selectedItemForQR && (
          <AssetQRCode 
            entityType="inventory"
            entityId={selectedItemForQR.id}
            organisationId={user?.organisation_id || 0}
            label={selectedItemForQR.name}
            code={selectedItemForQR.sku}
          />
        )}
      </Modal>
    </motion.div>
  );
};

export default Inventory;
