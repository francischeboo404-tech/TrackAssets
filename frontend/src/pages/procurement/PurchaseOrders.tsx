import React, { useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import {
  FileText,
  Plus,
  CheckCircle2,
  Clock,
  XCircle,
  Search,
  Filter,
  Trash2,
} from "lucide-react";
import {
  usePurchaseOrders,
  useCreatePurchaseOrder,
  useCanvassPurchaseOrder,
  useApprovePurchaseOrder,
  useRejectPurchaseOrder,
} from "../../hooks/usePurchaseOrders";
import { usePurchaseRequests } from "../../hooks/useProcurement";
import { useRequisitions } from "../../hooks/useRequisitions";
import { useInventory } from "../../hooks/useInventory";
import { useSuppliers } from "../../hooks/useSuppliers";
import { useToast } from "../../context/ToastContext";
import ViewPOModal from "../../components/ui/ViewPOModal";


export default function PurchaseOrders() {
  const [showForm, setShowForm] = useState(false);
  const [viewModalId, setViewModalId] = useState<number | null>(null);
  const [searchQuery, setSearchQuery] = useState("");
  const [statusFilter, setStatusFilter] = useState("all");

  // Form State
  const [prId, setPrId] = useState("");
  const [risId, setRisId] = useState("");
  const [supplierId, setSupplierId] = useState("");
  const [items, setItems] = useState<any[]>([]);

  const { addToast } = useToast();

  const { data: ordersData, isLoading } = usePurchaseOrders() as any;
  const { data: prsData } = usePurchaseRequests() as any;
  const { data: risData } = useRequisitions() as any;
  const { data: inventoryData } = useInventory();
  const { data: suppliersData } = useSuppliers() as any;

  const createPO = useCreatePurchaseOrder();
  const canvassPO = useCanvassPurchaseOrder();
  const approvePO = useApprovePurchaseOrder();
  const rejectPO = useRejectPurchaseOrder();


  const [showCanvassModal, setShowCanvassModal] = useState(false);
  const [selectedPO, setSelectedPO] = useState<number | null>(null);
  const [supplierName, setSupplierName] = useState("");
  const [itemName, setItemName] = useState("");
  const [unitCost, setUnitCost] = useState("");

  const orders = Array.isArray(ordersData?.purchase_orders)
    ? ordersData.purchase_orders
    : Array.isArray(ordersData)
      ? ordersData
      : [];

  const rawPRs = Array.isArray(prsData?.purchase_requests)
    ? prsData.purchase_requests
    : Array.isArray(prsData)
      ? prsData
      : [];
  const purchaseRequests = rawPRs.filter((pr: any) => pr.status === "approved");

  const rawRis = Array.isArray(risData?.items)
    ? risData.items
    : Array.isArray(risData?.requisitions)
      ? risData.requisitions
      : Array.isArray(risData)
        ? risData
        : [];
  const requisitions = rawRis.filter((r: any) => r.status === "approved");

  const inventory = inventoryData?.inventory || [];
  const suppliers = Array.isArray(suppliersData?.suppliers)
    ? suppliersData.suppliers
    : [];

  const handleSourceChange = (type: "pr" | "ris", id: string) => {
    if (type === "pr") {
      setPrId(id);
      setRisId("");
      const pr = purchaseRequests.find((p: any) => p.id === Number(id));
      if (pr && pr.items) {
        setItems(
          pr.items.map((it: any) => ({
            item_id: it.item_id,
            quantity: it.quantity,
            unit_cost: it.estimated_cost || 0,
          })),
        );
      } else {
        setItems([]);
      }
    } else {
      setRisId(id);
      setPrId("");
      const ris = requisitions.find((r: any) => r.id === Number(id));
      if (ris && ris.items) {
        setItems(
          ris.items.map((it: any) => ({
            item_id: it.item_id,
            quantity: it.quantity_requested || it.quantity || 1,
            unit_cost: it.unit_cost || 0,
          })),
        );
      } else {
        setItems([]);
      }
    }
  };

  const handleAddItem = () => {
    setItems([...items, { item_id: "", quantity: 1, unit_cost: 0 }]);
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
    if (!prId && !risId) {
      addToast(
        "error",
        "Validation Error",
        "Please select either a Purchase Request or a Requisition.",
      );
      return;
    }
    if (!supplierId || isNaN(Number(supplierId))) {
      addToast(
        "error",
        "Validation Error",
        "Please enter a valid Supplier ID.",
      );
      return;
    }
    if (items.length === 0) {
      addToast(
        "error",
        "Validation Error",
        "Please add at least one item to the PO.",
      );
      return;
    }

    // Format payload
    const formattedItems = items.map((item) => ({
      item_id: Number(item.item_id),
      quantity: Number(item.quantity),
      unit_cost: Number(item.unit_cost),
      total_cost: Number(item.quantity) * Number(item.unit_cost),
    }));

    try {
      await createPO.mutateAsync({
        pr_id: prId ? Number(prId) : undefined,
        ris_id: risId ? Number(risId) : undefined,
        supplier_id: Number(supplierId),
        items: formattedItems,
      });
      addToast("success", "Success", "Purchase order created successfully");
      setShowForm(false);
      setPrId("");
      setSupplierId("");
      setItems([]);
    } catch (err: any) {
      addToast(
        "error",
        "Create failed",
        err.response?.data?.message || "Could not create PO",
      );
    }
  };

  const handleApprove = async (id: number) => {
    try {
      await approvePO.mutateAsync(id);
      addToast(
        "success",
        "Purchase Order Approved",
        `PO #${id} has been approved.`,
      );
    } catch (err: any) {
      addToast(
        "error",
        "Approval Failed",
        err.response?.data?.message || "Could not approve this purchase order.",
      );
    }
  };

  const handleReject = async (id: number) => {
    try {
      await rejectPO.mutateAsync(id);
      addToast(
        "success",
        "Purchase Order Rejected",
        `PO #${id} has been rejected.`,
      );
    } catch (err: any) {
      addToast(
        "error",
        "Rejection Failed",
        err.response?.data?.message || "Could not reject this purchase order.",
      );
    }
  };

  const filteredOrders = orders.filter((po: any) => {
    const matchesSearch =
      po.po_number?.toLowerCase().includes(searchQuery.toLowerCase()) ||
      po.supplier_id?.toString().includes(searchQuery.toLowerCase());
    const matchesStatus = statusFilter === "all" || po.status === statusFilter;
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
            <div className="p-2 bg-indigo-100 rounded-xl">
              <FileText className="w-6 h-6 text-indigo-600" />
            </div>
            Purchase Orders
          </h1>
          <p className="text-slate-500 mt-1">
            Manage vendor orders, canvassing and approvals (KES).
          </p>
        </div>
        <button
          onClick={() => setShowForm((s) => !s)}
          className="btn-primary flex items-center justify-center gap-2"
        >
          {showForm ? (
            "Cancel"
          ) : (
            <>
              <Plus className="w-4 h-4" /> Create PO
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
            className="glass-panel p-6 overflow-hidden"
          >
            <h2 className="text-lg font-bold text-slate-800 mb-4">
              New Purchase Order
            </h2>
            <form onSubmit={handleSubmit} className="space-y-6">
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-semibold text-slate-700 mb-1">
                    Approved Purchase Request
                  </label>
                  <select
                    disabled={!!risId}
                    value={prId}
                    onChange={(e) => handleSourceChange("pr", e.target.value)}
                    className="input-field w-full"
                  >
                    <option value="">Select a PR</option>
                    {purchaseRequests.map((pr: any) => (
                      <option key={pr.id} value={pr.id}>
                        {pr.pr_number} - {pr.reason}
                      </option>
                    ))}
                  </select>
                </div>
                <div>
                  <label className="block text-sm font-semibold text-slate-700 mb-1">
                    Approved Requisition
                  </label>
                  <select
                    disabled={!!prId}
                    value={risId}
                    onChange={(e) => handleSourceChange("ris", e.target.value)}
                    className="input-field w-full"
                  >
                    <option value="">Select a Requisition</option>
                    {requisitions.map((ris: any) => (
                      <option key={ris.id} value={ris.id}>
                        {ris.ris_number} - {ris.department_name || "Dept"}
                      </option>
                    ))}
                  </select>
                </div>
                <div>
                  <label className="block text-sm font-semibold text-slate-700 mb-1">
                    Supplier <span className="text-rose-500">*</span>
                  </label>
                  <select
                    required
                    value={supplierId}
                    onChange={(e) => setSupplierId(e.target.value)}
                    className="input-field w-full"
                  >
                    <option value="">Select a Supplier</option>
                    {suppliers.map((s: any) => (
                      <option key={s.id} value={s.id}>
                        {s.name} ({s.code || `ID: ${s.id}`})
                      </option>
                    ))}
                  </select>
                </div>
              </div>

              <div className="space-y-3">
                <div className="flex items-center justify-between">
                  <label className="block text-sm font-semibold text-slate-700">
                    Order Items
                  </label>
                  <button
                    type="button"
                    onClick={handleAddItem}
                    className="text-sm font-bold text-indigo-600 hover:text-indigo-700 flex items-center gap-1"
                  >
                    <Plus className="w-4 h-4" /> Add Item
                  </button>
                </div>

                {items.length === 0 ? (
                  <div className="p-6 border-2 border-dashed border-slate-200 rounded-xl text-center text-slate-500 text-sm">
                    No items added yet. Click "Add Item" to build the PO.
                  </div>
                ) : (
                  <div className="space-y-3">
                    {items.map((item, idx) => (
                      <div
                        key={idx}
                        className="flex flex-wrap md:flex-nowrap items-end gap-3 p-4 bg-slate-50 border border-slate-100 rounded-xl"
                      >
                        <div className="flex-1 min-w-[200px]">
                          <label className="block text-xs font-semibold text-slate-500 mb-1">
                            Item
                          </label>
                          <select
                            required
                            value={item.item_id}
                            onChange={(e) =>
                              handleItemChange(idx, "item_id", e.target.value)
                            }
                            className="input-field w-full py-2"
                          >
                            <option value="">Select Item</option>
                            {inventory.map((inv: any) => (
                              <option key={inv.id} value={inv.id}>
                                {inv.name} ({inv.sku})
                              </option>
                            ))}
                          </select>
                        </div>
                        <div className="w-full md:w-32">
                          <label className="block text-xs font-semibold text-slate-500 mb-1">
                            Qty
                          </label>
                          <input
                            type="number"
                            min="1"
                            required
                            value={item.quantity}
                            onChange={(e) =>
                              handleItemChange(idx, "quantity", e.target.value)
                            }
                            className="input-field w-full py-2"
                          />
                        </div>
                        <div className="w-full md:w-40">
                          <label className="block text-xs font-semibold text-slate-500 mb-1">
                            Unit Cost (KES)
                          </label>
                          <input
                            type="number"
                            min="0"
                            step="0.01"
                            required
                            value={item.unit_cost}
                            onChange={(e) =>
                              handleItemChange(idx, "unit_cost", e.target.value)
                            }
                            className="input-field w-full py-2"
                            placeholder="0.00"
                          />
                        </div>
                        <div className="w-full md:w-40">
                          <label className="block text-xs font-semibold text-slate-500 mb-1">
                            Total Cost
                          </label>
                          <input
                            type="text"
                            readOnly
                            value={(item.quantity * item.unit_cost).toFixed(2)}
                            className="input-field w-full py-2 bg-slate-100 text-slate-500 cursor-not-allowed"
                          />
                        </div>
                        <button
                          type="button"
                          onClick={() => handleRemoveItem(idx)}
                          className="p-2 text-rose-500 hover:bg-rose-50 rounded-lg transition-colors"
                        >
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
                <button
                  type="submit"
                  className="btn-primary"
                  disabled={createPO.isPending}
                >
                  {createPO.isPending ? "Submitting..." : "Submit PO"}
                </button>
              </div>
            </form>
          </motion.div>
        )}
      </AnimatePresence>

      <div className="enterprise-card overflow-hidden p-0">
        <div className="p-4 border-b border-slate-100 bg-slate-50/50 flex flex-wrap items-center justify-between gap-4">
          <h3 className="font-bold text-slate-700">Recent Purchase Orders</h3>
          <div className="flex items-center gap-3">
            <div className="relative">
              <Search className="w-4 h-4 text-slate-400 absolute left-3 top-1/2 -translate-y-1/2" />
              <input
                type="text"
                placeholder="Search POs..."
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
                <option value="received">Received</option>
                <option value="partially_received">Partially Received</option>
              </select>
            </div>
          </div>
        </div>
        <div className="table-container">
          <table className="w-full text-left border-collapse responsive-table">
            <thead>
              <tr className="bg-slate-50 border-b border-slate-100">
                <th className="table-header px-6 py-4 text-xs font-bold text-slate-500 uppercase tracking-wider">
                  PO Number
                </th>
                <th className="table-header px-6 py-4 text-xs font-bold text-slate-500 uppercase tracking-wider">
                  Total Amount
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
                    Loading purchase orders...
                  </td>
                </tr>
              ) : (
                filteredOrders.map((po: any) => (
                  <tr
                    key={po.id}
                    className="table-row hover:bg-slate-50 transition-colors"
                  >
                    <td
                      data-label="Detail"
                      className="table-cell px-6 py-4 font-semibold text-slate-800 whitespace-nowrap"
                    >
                      {po.po_number ?? `PO-${po.id}`}
                    </td>
                    <td
                      data-label="Detail"
                      className="table-cell px-6 py-4 text-slate-600 font-medium"
                    >
                      KES{" "}
                      {Number(po.total_amount).toLocaleString(undefined, {
                        minimumFractionDigits: 2,
                      })}
                    </td>
                    <td
                      data-label="Detail"
                      className="table-cell px-6 py-4 text-slate-500 text-sm whitespace-nowrap"
                    >
                      {po.created_at
                        ? new Date(po.created_at).toLocaleDateString()
                        : "—"}
                    </td>
                    <td
                      data-label="Detail"
                      className="table-cell px-6 py-4 whitespace-nowrap"
                    >
                      <span
                        className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-bold ${["approved", "received"].includes(po.status)
                          ? "bg-emerald-100 text-emerald-700"
                          : po.status === "rejected" ||
                            po.status === "cancelled"
                            ? "bg-rose-100 text-rose-700"
                            : po.status === "partially_received"
                              ? "bg-blue-100 text-blue-700"
                              : "bg-amber-100 text-amber-700"
                          }`}
                      >
                        {["approved", "received"].includes(po.status) && (
                          <CheckCircle2 className="w-3.5 h-3.5" />
                        )}
                        {["rejected", "cancelled"].includes(po.status) && (
                          <XCircle className="w-3.5 h-3.5" />
                        )}
                        {po.status === "pending" && (
                          <Clock className="w-3.5 h-3.5" />
                        )}
                        {String(po.status).toUpperCase().replace("_", " ")}
                      </span>
                    </td>
                    <td
                      data-label="Detail"
                      className="table-cell px-6 py-4 text-right whitespace-nowrap"
                    >
                      <div className="flex gap-2 justify-end">
                        {po.status === "pending" && (
                          <>
                            <button
                              type="button"
                              onClick={() => {
                                setSelectedPO(po.id);
                                setShowCanvassModal(true);
                              }}
                              className="text-sm font-semibold text-blue-600 bg-blue-50 px-3 py-1.5 rounded-lg">
                              Quote
                            </button>
                            <button
                              type="button"
                              onClick={() => handleApprove(po.id)}
                              disabled={approvePO.isPending}
                              className="text-sm font-semibold text-emerald-600 hover:text-emerald-700 bg-emerald-50 px-3 py-1.5 rounded-lg transition-colors disabled:cursor-not-allowed disabled:opacity-60">

                              Approve
                            </button>
                            <button
                              type="button"
                              onClick={() => handleReject(po.id)}
                              disabled={rejectPO.isPending}
                              className="text-sm font-semibold text-rose-600 hover:text-rose-700 bg-rose-50 px-3 py-1.5 rounded-lg transition-colors disabled:cursor-not-allowed disabled:opacity-60"
                            >
                              Reject
                            </button>
                          </>
                        )}
                        <button
                          className="text-sm font-semibold text-indigo-600 hover:text-indigo-700 bg-indigo-50 px-3 py-1.5 rounded-lg transition-colors"
                          onClick={() => setViewModalId(po.id)}
                        >
                          View
                        </button>
                      </div>
                    </td>
                  </tr>
                ))
              )}
              {!isLoading && filteredOrders.length === 0 && (
                <tr>
                  <td colSpan={5} className="px-6 py-12 text-center">
                    <div className="mx-auto w-12 h-12 bg-slate-100 rounded-full flex items-center justify-center mb-3">
                      <FileText className="w-6 h-6 text-slate-400" />
                    </div>
                    <p className="text-slate-500 font-medium">
                      No purchase orders found.
                    </p>
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </div>
      <ViewPOModal
        isOpen={!!viewModalId}
        onClose={() => setViewModalId(null)}
        poId={viewModalId}
      />


      {showCanvassModal && (
        <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50">
          <div className="bg-white rounded-xl p-6 w-[450px]">
            <h2 className="text-xl font-bold mb-4">Add Canvass Quote</h2>
            <input
              className="input-field w-full mb-3"
              placeholder="Supplier Name"
              value={supplierName}
              onChange={(e) => setSupplierName(e.target.value)}
            />

            <input
              className="input-field w-full mb-3"
              placeholder="Item Name"
              value={itemName}
              onChange={(e) => setItemName(e.target.value)}
            />

            <input
              type="number"
              className="input-field w-full mb-4"
              placeholder="Unit Cost"
              value={unitCost}
              onChange={(e) => setUnitCost(e.target.value)}
            />
            <div className="flex justify-end gap-3">
              <button
                className="btn-primary"
                onClick={async () => {
                  try {
                    await canvassPO.mutateAsync({
                      id: selectedPO!,
                      supplier_name: supplierName,
                      item_name: itemName,
                      unit_cost: Number(unitCost),
                    });

                    addToast(
                      "success",
                      "Quote Added",
                      "Canvass quotation added successfully."
                    );

                    setShowCanvassModal(false);
                    setSupplierName("");
                    setItemName("");
                    setUnitCost("");
                  } catch (err: any) {
                    addToast(
                      "error",
                      "Failed",
                      err.response?.data?.message || "Failed to add canvass quote."
                    );
                  }
                }}
              >
                Save Quote
              </button>
            </div>
          </div>
        </div>
      )
      }
    </motion.div >
  );
}
