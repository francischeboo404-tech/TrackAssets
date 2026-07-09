import React, { useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { ShoppingCart, Plus, CheckCircle2, XCircle, Clock, Trash2, Search, Filter } from "lucide-react";
import { useQueryClient } from "@tanstack/react-query";
import { usePurchaseRequests, useCreatePurchaseRequest, useApprovePurchaseRequest, useRejectPurchaseRequest } from '../../hooks/useProcurement';
import ViewPRModal from '../../components/ui/ViewPRModal';
import { useInventory } from '../../hooks/useInventory';
import { useAssets } from '../../hooks/useAssets';
import { useToast } from "../../context/ToastContext";
import { useWarehouse } from '../../context/WarehouseContext';

export default function PurchaseRequests() {
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [viewModalId, setViewModalId] = useState<number | null>(null);
  const [showForm, setShowForm] = useState(false);
  const [searchQuery, setSearchQuery] = useState("");
  const [statusFilter, setStatusFilter] = useState("all");
  
  // Form State
  const [reason, setReason] = useState("");
  const [items, setItems] = useState<any[]>([]);

  const { addToast } = useToast();
  const queryClient = useQueryClient();
  const { activeWarehouseId } = useWarehouse();

  const { data: requestsData, isLoading } = usePurchaseRequests(activeWarehouseId) as any;
  const { data: inventoryData } = useInventory(activeWarehouseId ? { warehouse_id: activeWarehouseId } : {});
  const { data: assetsData } = useAssets(activeWarehouseId ? { per_page: 100, warehouse_id: activeWarehouseId } : { per_page: 100 });
  
  const createPR = useCreatePurchaseRequest();
  const approvePR = useApprovePurchaseRequest();
  const rejectPR = useRejectPurchaseRequest();

  const requests = requestsData?.purchase_requests || requestsData || [];
  const inventory = inventoryData?.inventory || [];
  const assets = assetsData?.assets || [];

  const handleAddItem = () => {
    setItems([...items, { item_type: "inventory", item_id: "", asset_id: "", quantity: 1, estimated_cost: 0, justification: "" }]);
  };

  const handleRemoveItem = (index: number) => {
    setItems(items.filter((_, i) => i !== index));
  };

  const handleItemChange = (index: number, field: string, value: any) => {
    const newItems = [...items];
    if (field === "item_type") {
      newItems[index].item_type = value;
      newItems[index].item_id = "";
      newItems[index].asset_id = "";
    } else {
      newItems[index][field] = value;
    }
    setItems(newItems);
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (items.length === 0) {
      addToast("error", "Validation Error", "Please add at least one item to the request.");
      return;
    }
    
    const formattedItems = items.map(item => {
      const baseItem = {
        item_type: item.item_type || "inventory",
        quantity: Number(item.quantity),
        estimated_cost: Number(item.estimated_cost || 0),
        justification: item.justification || "",
      };
      if (item.item_type === "asset") {
        return { ...baseItem, asset_id: Number(item.asset_id), item_id: undefined };
      }
      return { ...baseItem, item_id: Number(item.item_id), asset_id: undefined };
    });

    try {
      await createPR.mutateAsync({ reason, items: formattedItems });
      addToast("success", "Success", "Purchase request submitted successfully");
      setShowForm(false);
      setReason("");
      setItems([]);
    } catch (err: any) {
      addToast("error", "Submit failed", err.response?.data?.message || 'Could not submit PR');
    }
  };

  const filteredRequests = requests.filter((pr: any) => {
    const matchesSearch = pr.pr_number?.toLowerCase().includes(searchQuery.toLowerCase()) || 
                          pr.reason?.toLowerCase().includes(searchQuery.toLowerCase());
    const matchesStatus = statusFilter === "all" || pr.status === statusFilter;
    return matchesSearch && matchesStatus;
  });

  return (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      className="space-y-6"
    >
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-3xl font-black text-slate-900 flex items-center gap-3">
            <div className="p-2 bg-brand-primary/10 rounded-xl">
              <ShoppingCart className="w-6 h-6 text-brand-primary" />
            </div>
            Purchase Requests
          </h1>
          <p className="text-slate-500 mt-1">
            Manage institutional procurement requests and view approvals.
          </p>
        </div>
        <button
          onClick={() => setShowForm(!showForm)}
          className="btn-primary flex items-center justify-center gap-2"
        >
          {showForm ? (
            "Cancel"
          ) : (
            <>
              <Plus className="w-4 h-4" /> Create Request
            </>
          )}
        </button>
      </div>

      <AnimatePresence>
        {showForm && (
          <motion.div
            initial={{ y: -20, opacity: 0, height: 0 }}
            animate={{ y: 0, opacity: 1, height: "auto" }}
            exit={{ opacity: 0, height: 0 }}
            className="enterprise-card p-6 overflow-hidden"
          >
            <h2 className="text-lg font-bold text-slate-800 mb-4">
              New Purchase Request
            </h2>
            <form className="space-y-6" onSubmit={handleSubmit}>
              <div>
                <label className="block text-sm font-semibold text-slate-700 mb-1">
                  Reason for Request <span className="text-rose-500">*</span>
                </label>
                <textarea
                  required
                  value={reason}
                  onChange={(e) => setReason(e.target.value)}
                  className="input-field min-h-[80px] w-full"
                  placeholder="Brief justification..."
                />
              </div>

              <div className="space-y-3">
                <div className="flex items-center justify-between">
                  <label className="block text-sm font-semibold text-slate-700">
                    Requested Items
                  </label>
                  <button type="button" onClick={handleAddItem} className="text-sm font-bold text-brand-primary hover:text-brand-primary/80 flex items-center gap-1">
                    <Plus className="w-4 h-4" /> Add Item
                  </button>
                </div>
                
                {items.length === 0 ? (
                  <div className="p-6 border-2 border-dashed border-slate-200 rounded-xl text-center text-slate-500 text-sm">
                    No items added yet. Click "Add Item" to request inventory.
                  </div>
                ) : (
                  <div className="space-y-3">
                    {items.map((item, idx) => (
                      <div key={idx} className="flex flex-wrap md:flex-nowrap items-end gap-3 p-4 bg-slate-50 border border-slate-100 rounded-xl">
                        <div className="w-full md:w-40">
                          <label className="block text-xs font-semibold text-slate-500 mb-1">Type</label>
                          <select value={item.item_type || "inventory"} onChange={(e) => handleItemChange(idx, "item_type", e.target.value)} className="input-field w-full py-2">
                            <option value="inventory">Inventory</option>
                            <option value="asset">Asset</option>
                          </select>
                        </div>
                        <div className="flex-1 min-w-[200px]">
                          <label className="block text-xs font-semibold text-slate-500 mb-1">{item.item_type === "asset" ? "Asset" : "Item"}</label>
                          <select required value={item.item_type === "asset" ? item.asset_id : item.item_id} onChange={(e) => handleItemChange(idx, item.item_type === "asset" ? "asset_id" : "item_id", e.target.value)} className="input-field w-full py-2">
                            <option value="">Select {item.item_type === "asset" ? "Asset" : "Item"}</option>
                            {item.item_type === "asset"
                              ? assets.map((asset: any) => (
                                  <option key={asset.id} value={asset.id}>{asset.name} ({asset.asset_code || asset.code})</option>
                                ))
                              : inventory.map((inv: any) => (
                                  <option key={inv.id} value={inv.id}>{inv.name} ({inv.sku})</option>
                                ))}
                          </select>
                        </div>
                        <div className="w-full md:w-32">
                          <label className="block text-xs font-semibold text-slate-500 mb-1">Qty</label>
                          <input type="number" min="1" required value={item.quantity} onChange={(e) => handleItemChange(idx, "quantity", e.target.value)} className="input-field w-full py-2" />
                        </div>
                        <div className="w-full md:w-40">
                          <label className="block text-xs font-semibold text-slate-500 mb-1">Est. Cost</label>
                          <input type="number" min="0" step="0.01" value={item.estimated_cost} onChange={(e) => handleItemChange(idx, "estimated_cost", e.target.value)} className="input-field w-full py-2" placeholder="0.00" />
                        </div>
                        <div className="flex-1 min-w-[200px]">
                          <label className="block text-xs font-semibold text-slate-500 mb-1">Justification</label>
                          <input type="text" value={item.justification} onChange={(e) => handleItemChange(idx, "justification", e.target.value)} className="input-field w-full py-2" placeholder="Optional notes" />
                        </div>
                        <button type="button" onClick={() => handleRemoveItem(idx)} className="p-2 text-rose-500 hover:bg-rose-50 rounded-lg transition-colors">
                          <Trash2 className="w-5 h-5" />
                        </button>
                      </div>
                    ))}
                  </div>
                )}
              </div>

              <div className="flex justify-end gap-3 pt-4 border-t border-slate-100">
                <button
                  type="button"
                  onClick={() => setShowForm(false)}
                  className="btn-secondary"
                >
                  Cancel
                </button>
                <button type="submit" className="btn-primary" disabled={createPR.isPending}>
                  {createPR.isPending ? 'Submitting...' : 'Submit PR'}
                </button>
              </div>
            </form>
          </motion.div>
        )}
      </AnimatePresence>

      <div className="enterprise-card overflow-hidden p-0">
        <div className="p-4 border-b border-slate-100 bg-slate-50/50 flex flex-wrap items-center justify-between gap-4">
          <h3 className="font-bold text-slate-700">Recent Requests</h3>
          <div className="flex items-center gap-3">
            <div className="relative">
              <Search className="w-4 h-4 text-slate-400 absolute left-3 top-1/2 -translate-y-1/2" />
              <input
                type="text"
                placeholder="Search PRs..."
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
                <option value="pending">Pending</option>
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
                <th className="table-header px-6 py-4 text-xs font-bold text-slate-500 uppercase tracking-wider">
                  PR Number
                </th>
                <th className="table-header px-6 py-4 text-xs font-bold text-slate-500 uppercase tracking-wider">
                  Reason
                </th>
                <th className="table-header px-6 py-4 text-xs font-bold text-slate-500 uppercase tracking-wider">
                  Date
                </th>
                <th className="table-header px-6 py-4 text-xs font-bold text-slate-500 uppercase tracking-wider">
                  Status
                </th>
                <th className="table-header px-6 py-4 text-xs font-bold text-slate-500 uppercase tracking-wider text-right">
                  Actions
                </th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {isLoading ? (
                <tr>
                  <td
                    colSpan={5}
                    className="px-6 py-8 text-center text-slate-400"
                  >
                    Loading requests...
                  </td>
                </tr>
              ) : (
                filteredRequests.map((pr: any) => (
                  <tr
                    key={pr.id}
                    className="table-row hover:bg-slate-50 transition-colors"
                  >
                    <td data-label="Detail" className="table-cell px-6 py-4 font-semibold text-slate-800 whitespace-nowrap">
                      {pr.pr_number}
                    </td>
                    <td data-label="Detail" className="table-cell px-6 py-4 text-slate-600 max-w-md truncate">{pr.reason}</td>
                    <td data-label="Detail" className="table-cell px-6 py-4 text-slate-500 text-sm whitespace-nowrap">
                      {new Date(pr.created_at).toLocaleDateString()}
                    </td>
                    <td data-label="Detail" className="table-cell px-6 py-4 whitespace-nowrap">
                      <span
                        className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-bold ${
                          pr.status === "approved"
                            ? "bg-emerald-100 text-emerald-700"
                            : pr.status === "rejected"
                              ? "bg-rose-100 text-rose-700"
                              : "bg-amber-100 text-amber-700"
                        }`}
                      >
                        {pr.status === "approved" && (
                          <CheckCircle2 className="w-3.5 h-3.5" />
                        )}
                        {pr.status === "rejected" && (
                          <XCircle className="w-3.5 h-3.5" />
                        )}
                        {pr.status === "pending" && (
                          <Clock className="w-3.5 h-3.5" />
                        )}
                        {pr.status.toUpperCase()}
                      </span>
                    </td>
                    <td data-label="Detail" className="table-cell px-6 py-4 text-right whitespace-nowrap">
                      <div className="flex gap-2 justify-end">
                        {pr.status === 'pending' && (
                          <>
                            <button
                              onClick={() => approvePR.mutateAsync(pr.id)}
                              className="text-sm font-semibold text-emerald-600 hover:text-emerald-700 bg-emerald-50 px-3 py-1.5 rounded-lg transition-colors"
                            >
                              Approve
                            </button>
                            <button
                              onClick={() => rejectPR.mutateAsync(pr.id)}
                              className="text-sm font-semibold text-rose-600 hover:text-rose-700 bg-rose-50 px-3 py-1.5 rounded-lg transition-colors"
                            >
                              Reject
                            </button>
                          </>
                        )}
                        <button 
                          className="text-sm font-semibold text-brand-primary hover:text-brand-primary/80 transition-colors bg-brand-primary/10 px-3 py-1.5 rounded-lg"
                          onClick={() => setViewModalId(pr.id)}
                        >
                          View
                        </button>
                      </div>
                    </td>
                  </tr>
                ))
              )}
              {!isLoading && filteredRequests.length === 0 && (
                <tr>
                  <td
                    colSpan={5}
                    className="px-6 py-12 text-center"
                  >
                    <div className="mx-auto w-12 h-12 bg-slate-100 rounded-full flex items-center justify-center mb-3">
                        <ShoppingCart className="w-6 h-6 text-slate-400" />
                    </div>
                    <p className="text-slate-500 font-medium">No purchase requests found.</p>
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </div>
      <ViewPRModal isOpen={!!viewModalId} onClose={() => setViewModalId(null)} prId={viewModalId} />
    </motion.div>
  );
}
