import React, { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { PackageOpen, Plus, CheckCircle2, Clock, XCircle, Search, Filter, Trash2, ShieldAlert } from 'lucide-react';
import { usePurchaseOrders } from '../../hooks/usePurchaseOrders';
import ViewGRNModal from '../../components/ui/ViewGRNModal';
import { Modal } from '../../components/ui/Modal';
import { useCreateGRN, useCreateIAR, useApproveGRN } from '../../hooks/useReceiving';
import { useInventory } from '../../hooks/useInventory';
import { useToast } from '../../context/ToastContext';
import api from '../../services/api';
import { useQuery } from '@tanstack/react-query';

// Additional hook for GRNs
const useGRNs = () => {
  return useQuery({
    queryKey: ['goods_receipts'],
    queryFn: async () => {
      const res = await api.get('/receiving/goods-receipts');
      return res.data.goods_receipts ?? res.data;
    },
  });
};

export default function GoodsReceipts() {
  const [showForm, setShowForm] = useState(false);
  const [viewModalId, setViewModalId] = useState<number | null>(null);
  const [searchQuery, setSearchQuery] = useState("");
  const [statusFilter, setStatusFilter] = useState("all");
  
  // Form State
  const [poId, setPoId] = useState("");
  const [invoiceNumber, setInvoiceNumber] = useState("");
  const [deliveryNoteNumber, setDeliveryNoteNumber] = useState("");
  const [items, setItems] = useState<any[]>([]);

  const { addToast } = useToast();

  const { data: ordersData } = usePurchaseOrders() as any;
  const { data: grnsData, isLoading } = useGRNs() as any;
  const { data: inventoryData } = useInventory();
  

  const [showIARModal, setShowIARModal] = useState(false);
  const [selectedGRN, setSelectedGRN] = useState<number | null>(null);

  const [inspectionStatus, setInspectionStatus] = useState("passed");
  const [inspectionRemarks, setInspectionRemarks] = useState("");


  const createGRN = useCreateGRN();
  const createIAR = useCreateIAR();
  const approveGRN = useApproveGRN();

  const purchaseOrders = (ordersData?.purchase_orders || ordersData || []).filter((po: any) => po.status === 'approved' || po.status === 'partially_received');
  const grns = grnsData?.goods_receipts || grnsData || [];
  const inventory = inventoryData?.inventory || [];

  const handleAddItem = () => {
    setItems([...items, { item_id: "", quantity_received: 1, unit_cost: 0, expiry_date: "" }]);
  };

  const handleRemoveItem = (index: number) => {
    setItems(items.filter((_, i) => i !== index));
  };

  const handleItemChange = (index: number, field: string, value: any) => {
    const newItems = [...items];
    newItems[index][field] = value;
    setItems(newItems);
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (items.length === 0) {
      addToast("error", "Validation Error", "Please add at least one received item.");
      return;
    }
    
    // Format payload
    const formattedItems = items.map(item => ({
      item_id: Number(item.item_id),
      quantity_received: Number(item.quantity_received),
      unit_cost: Number(item.unit_cost),
      expiry_date: item.expiry_date || undefined
    }));

    try {
      const res = await createGRN.mutateAsync({ 
        po_id: Number(poId), 
        items: formattedItems,
        invoice_number: invoiceNumber || undefined,
        delivery_note_number: deliveryNoteNumber || undefined
      });
      addToast('success', 'GRN Created', `GRN ${res.grn_number} registered in quarantine.`);
      setShowForm(false);
      setPoId("");
      setInvoiceNumber("");
      setDeliveryNoteNumber("");
      setItems([]);
    } catch (err: any) {
      addToast('error', 'Create failed', err.response?.data?.message || 'Could not create GRN');
    }
  };

  const filteredGRNs = grns.filter((grn: any) => {
    const matchesSearch = grn.grn_number?.toLowerCase().includes(searchQuery.toLowerCase()) || 
                          grn.po_id?.toString().includes(searchQuery.toLowerCase());
    const matchesStatus = statusFilter === "all" || grn.status === statusFilter;
    return matchesSearch && matchesStatus;
  });

  return (
    <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} className="space-y-6">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-3xl font-black text-slate-900 flex items-center gap-3">
            <div className="p-2 bg-emerald-100 rounded-xl">
              <PackageOpen className="w-6 h-6 text-emerald-600" />
            </div>
            Goods Receipt Notes
          </h1>
          <p className="text-slate-500 mt-1">Receive PO items into quarantine and track inspection statuses.</p>
        </div>
        <button onClick={() => setShowForm((s) => !s)} className="btn-primary flex items-center justify-center gap-2">
          {showForm ? 'Cancel' : (<><Plus className="w-4 h-4" /> Receive Goods</>)}
        </button>
      </div>

      <Modal isOpen={showForm} onClose={() => setShowForm(false)} title="New Goods Receipt (GRN)" size="2xl">
        <form onSubmit={handleSubmit} className="space-y-6">
          <div className="flex flex-col md:flex-row gap-4">
            <div className="flex-1">
              <label className="block text-sm font-semibold text-slate-700 mb-1">Select Purchase Order <span className="text-rose-500">*</span></label>
              <select required value={poId} onChange={(e) => setPoId(e.target.value)} className="input-field w-full">
                <option value="">Select an Approved PO</option>
                {purchaseOrders.map((p: any) => (
                  <option key={p.id} value={p.id}>{p.po_number ?? `PO-${p.id}`} — {String(p.status).replace('_', ' ').toUpperCase()}</option>
                ))}
              </select>
            </div>
            <div className="flex-1">
              <label className="block text-sm font-semibold text-slate-700 mb-1">Invoice Number</label>
              <input type="text" value={invoiceNumber} onChange={(e) => setInvoiceNumber(e.target.value)} placeholder="e.g. INV-2023-001" className="input-field w-full" />
            </div>
            <div className="flex-1">
              <label className="block text-sm font-semibold text-slate-700 mb-1">Delivery Note Number</label>
              <input type="text" value={deliveryNoteNumber} onChange={(e) => setDeliveryNoteNumber(e.target.value)} placeholder="e.g. DN-88902" className="input-field w-full" />
            </div>
          </div>

          <div className="space-y-3">
            <div className="flex items-center justify-between">
              <label className="block text-sm font-semibold text-slate-700">Received Items (Quarantine)</label>
              <button type="button" onClick={handleAddItem} className="text-sm font-bold text-emerald-600 hover:text-emerald-700 flex items-center gap-1">
                <Plus className="w-4 h-4" /> Add Item
              </button>
            </div>
            
            {items.length === 0 ? (
              <div className="p-6 border-2 border-dashed border-slate-200 rounded-xl text-center text-slate-500 text-sm">
                No items added. Click "Add Item" to record received goods.
              </div>
            ) : (
              <div className="space-y-3">
                {items.map((item, idx) => (
                  <div key={idx} className="flex flex-wrap md:flex-nowrap items-end gap-3 p-4 bg-amber-50/50 border border-amber-100 rounded-xl">
                    <div className="flex-1 min-w-[200px]">
                      <label className="block text-xs font-semibold text-slate-500 mb-1">Item</label>
                      <select required value={item.item_id} onChange={(e) => handleItemChange(idx, "item_id", e.target.value)} className="input-field w-full py-2">
                        <option value="">Select Item</option>
                        {inventory.map((inv: any) => (
                          <option key={inv.id} value={inv.id}>{inv.name} ({inv.sku})</option>
                        ))}
                      </select>
                    </div>
                    <div className="w-full md:w-32">
                      <label className="block text-xs font-semibold text-slate-500 mb-1">Qty Received</label>
                      <input type="number" min="1" required value={item.quantity_received} onChange={(e) => handleItemChange(idx, "quantity_received", e.target.value)} className="input-field w-full py-2" />
                    </div>
                    <div className="w-full md:w-40">
                      <label className="block text-xs font-semibold text-slate-500 mb-1">Unit Cost (PO Match)</label>
                      <input type="number" min="0" step="0.01" required value={item.unit_cost} onChange={(e) => handleItemChange(idx, "unit_cost", e.target.value)} className="input-field w-full py-2" placeholder="0.00" />
                    </div>
                    <div className="w-full md:w-40">
                      <label className="block text-xs font-semibold text-slate-500 mb-1">Expiry (Optional)</label>
                      <input type="date" value={item.expiry_date} onChange={(e) => handleItemChange(idx, "expiry_date", e.target.value)} className="input-field w-full py-2" />
                    </div>
                    <button type="button" onClick={() => handleRemoveItem(idx)} className="p-2 text-rose-500 hover:bg-rose-50 rounded-lg transition-colors mt-4 md:mt-0">
                      <Trash2 className="w-5 h-5" />
                    </button>
                  </div>
                ))}
              </div>
            )}
          </div>

          <div className="flex justify-end gap-3 pt-4 border-t border-slate-100">
            <button type="button" onClick={() => setShowForm(false)} className="btn-secondary">Cancel</button>
            <button type="submit" className="btn-primary" disabled={createGRN.isPending}>
              {createGRN.isPending ? 'Submitting...' : 'Register GRN'}
            </button>
          </div>
        </form>
      </Modal>

      <div className="enterprise-card overflow-hidden p-0">
        <div className="p-4 border-b border-slate-100 bg-slate-50/50 flex flex-wrap items-center justify-between gap-4">
          <h3 className="font-bold text-slate-700">Recent Goods Receipts</h3>
          <div className="flex items-center gap-3">
            <div className="relative">
              <Search className="w-4 h-4 text-slate-400 absolute left-3 top-1/2 -translate-y-1/2" />
              <input
                type="text"
                placeholder="Search GRNs..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="input-field pl-9 py-1.5 text-sm w-48 focus:w-64 transition-all"
              />
            </div>
            <div className="relative">
              <Filter className="w-4 h-4 text-slate-400 absolute left-3 top-1/2 -translate-y-1/2" />
              <select
                value={statusFilter}
                onChange={(e) => setStatusFilter(e.target.value)}
                className="input-field pl-9 py-1.5 text-sm appearance-none"
              >
                <option value="all">All Statuses</option>
                <option value="quarantine">Quarantine</option>
                <option value="approved">Approved</option>
                <option value="rejected">Rejected</option>
              </select>
            </div>
          </div>
        </div>
        <div className="table-container">
          <table className="w-full text-left border-collapse responsive-table">
            <thead>
              <tr className="bg-slate-50 border-b border-slate-100">
                <th className="table-header px-6 py-4 text-xs font-bold text-slate-500 uppercase tracking-wider">GRN Number</th>
                <th className="table-header px-6 py-4 text-xs font-bold text-slate-500 uppercase tracking-wider">PO Number</th>
                <th className="table-header px-6 py-4 text-xs font-bold text-slate-500 uppercase tracking-wider">Documents</th>
                <th className="table-header px-6 py-4 text-xs font-bold text-slate-500 uppercase tracking-wider">Total Qty</th>
                <th className="table-header px-6 py-4 text-xs font-bold text-slate-500 uppercase tracking-wider">Date</th>
                <th className="table-header px-6 py-4 text-xs font-bold text-slate-500 uppercase tracking-wider">Status</th>
                <th className="table-header px-6 py-4 text-xs font-bold text-slate-500 uppercase tracking-wider text-right">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {isLoading ? (
                <tr><td colSpan={6} className="px-6 py-8 text-center text-slate-400">Loading goods receipts...</td></tr>
              ) : (
                filteredGRNs.map((grn: any) => (
                  <tr key={grn.id} className="table-row hover:bg-slate-50 transition-colors">
                    <td data-label="GRN" className="table-cell px-6 py-4 font-semibold text-slate-800 whitespace-nowrap">{grn.grn_number}</td>
                    <td data-label="PO" className="table-cell px-6 py-4 text-slate-600 font-medium">PO-{grn.po_id}</td>
                    <td data-label="Docs" className="table-cell px-6 py-4 text-slate-600 font-medium">
                      <div className="text-sm">Inv: {grn.invoice_number || '—'}</div>
                      <div className="text-xs text-slate-400">DN: {grn.delivery_note_number || '—'}</div>
                    </td>
                    <td data-label="Qty" className="table-cell px-6 py-4 text-slate-600 font-medium">{grn.total_quantity}</td>
                    <td data-label="Date" className="table-cell px-6 py-4 text-slate-500 text-sm whitespace-nowrap">{grn.created_at ? new Date(grn.created_at).toLocaleDateString() : '—'}</td>
                    <td data-label="Status" className="table-cell px-6 py-4 whitespace-nowrap">
                      <span className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-bold ${
                        ['approved'].includes(grn.status) ? 'bg-emerald-100 text-emerald-700' : 
                        grn.status === 'rejected' ? 'bg-rose-100 text-rose-700' : 
                        grn.status === 'quarantine' ? 'bg-amber-100 text-amber-700' :
                        'bg-blue-100 text-blue-700'
                      }`}>
                        {['approved'].includes(grn.status) && <CheckCircle2 className="w-3.5 h-3.5" />}
                        {['rejected'].includes(grn.status) && <XCircle className="w-3.5 h-3.5" />}
                        {grn.status === 'quarantine' && <ShieldAlert className="w-3.5 h-3.5" />}
                        {String(grn.status).toUpperCase().replace('_', ' ')}
                      </span>
                    </td>
                    <td data-label="Detail" className="table-cell px-6 py-4 text-right whitespace-nowrap">
                      <div className="flex gap-2 justify-end">
                        {grn.status === 'quarantine' && (
                          <>
                            <button className="text-sm font-semibold text-blue-600 hover:text-blue-700 bg-blue-50 px-3 py-1.5 rounded-lg" onClick={() => {setSelectedGRN(grn.id); setShowIARModal(true);}}>
                              Inspect
</button>
                          </>
                        )}
                        <button 
                          className="text-sm font-semibold text-brand-primary hover:text-brand-primary/80 transition-colors bg-brand-primary/10 px-3 py-1.5 rounded-lg"
                          onClick={() => setViewModalId(grn.id)}
                        >
                          View
                        </button>
                      </div>
                    </td>
                  </tr>
                ))
              )}
              {!isLoading && filteredGRNs.length === 0 && (
                <tr>
                  <td colSpan={6} className="px-6 py-12 text-center">
                    <div className="mx-auto w-12 h-12 bg-slate-100 rounded-full flex items-center justify-center mb-3">
                        <PackageOpen className="w-6 h-6 text-slate-400" />
                    </div>
                    <p className="text-slate-500 font-medium">No goods receipt notes found.</p>
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </div>
      <Modal isOpen={showIARModal} onClose={() => setShowIARModal(false)} title="Inspection Report">
        <div className="space-y-4">

          <div>
            <label className="block text-sm font-semibold">
              Inspection Result
            </label>

            <select value={inspectionStatus} onChange={(e) => setInspectionStatus(e.target.value)} className="input-field w-full">
              <option value="passed">Passed</option>
              <option value="failed">Failed</option>
            </select>
          </div>

          <div>
            <label className="block text-sm font-semibold">
              Remarks
            </label>

            <textarea rows={4} value={inspectionRemarks} onChange={(e) => setInspectionRemarks(e.target.value)} className="input-field w-full"/>
          </div>

          <div className="flex justify-end gap-3">

            <button className="btn-secondary" onClick={() => setShowIARModal(false)}>
              Cancel
            </button>

            <button className="btn-primary" onClick={async () => {
              try {
                  console.log("Creating IAR...");

                  const iar = await createIAR.mutateAsync({
                    grn_id: selectedGRN!,
                    status: inspectionStatus,
                    remarks: inspectionRemarks,
                  });

                  console.log("IAR created:", iar);

                  console.log("Approving GRN...");

                  const approval = await approveGRN.mutateAsync(selectedGRN!);

                  console.log("Approved:", approval);

                  addToast("success", "Inspection Completed", "GRN approved successfully.");

                  setShowIARModal(false);

                } catch (err: any) {
                  console.error(err);

                  console.error(err.response?.data);

                  addToast("error", "Inspection Failed", err.response?.data?.message ?? "Unable to approve GRN");
                }
              }
            }>
              Save & Approve
            </button>

          </div>

        </div>
      </Modal>
      <ViewGRNModal isOpen={!!viewModalId} onClose={() => setViewModalId(null)} grnId={viewModalId} />
    </motion.div>
  );
}
