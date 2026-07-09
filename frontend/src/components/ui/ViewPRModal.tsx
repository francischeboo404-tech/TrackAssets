import React from "react";
import {
  X,
  FileText,
  CheckCircle2,
  Clock,
  XCircle,
  ShoppingCart,
} from "lucide-react";
import { useQuery } from "@tanstack/react-query";
import api from "../../services/api";
import { Modal } from "./Modal";

interface ViewPRModalProps {
  isOpen: boolean;
  onClose: () => void;
  prId: number | null;
}

export default function ViewPRModal({
  isOpen,
  onClose,
  prId,
}: ViewPRModalProps) {
  const { data: pr, isLoading } = useQuery({
    queryKey: ["purchaseRequest", prId],
    queryFn: async () => {
      if (!prId) return null;
      const res = await api.get(`/procurement/purchase-requests/${prId}`);
      return res.data;
    },
    enabled: !!prId,
  });

  if (!isOpen) return null;

  return (
    <Modal isOpen={isOpen} onClose={onClose} title={pr?.pr_number || 'Loading PR...'} size="2xl">
      <div className="space-y-8">
        <div className="flex flex-col gap-4 p-6 border-b border-slate-100 bg-slate-50/60 md:flex-row md:items-center md:justify-between">
          <div className="flex items-center gap-3 min-w-0">
            <div className="p-2.5 bg-blue-100 rounded-xl shrink-0">
              <ShoppingCart className="w-5 h-5 text-blue-600" />
            </div>
            <div className="min-w-0">
              <h2 className="text-xl font-bold text-slate-800 tracking-tight truncate">
                {pr?.pr_number || "Loading PR..."}
              </h2>
              <p className="text-sm text-slate-500 font-medium">
                {pr?.created_at ? new Date(pr.created_at).toLocaleDateString() : ""}
              </p>
            </div>
          </div>

          <div className="flex flex-wrap items-center gap-3 justify-end">
            {pr && (
              <span
                className={`inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-bold uppercase tracking-wider ${
                  pr.status === "approved"
                    ? "bg-emerald-100 text-emerald-700"
                    : pr.status === "rejected"
                      ? "bg-rose-100 text-rose-700"
                      : "bg-amber-100 text-amber-700"
                }`}
              >
                {pr.status === "approved" && (
                  <CheckCircle2 className="w-4 h-4" />
                )}
                {pr.status === "rejected" && <XCircle className="w-4 h-4" />}
                {pr.status === "pending" && <Clock className="w-4 h-4" />}
                {pr.status}
              </span>
            )}
            <button
              onClick={onClose}
              className="p-2 text-slate-400 hover:text-slate-600 hover:bg-slate-100 rounded-xl transition-colors"
            >
              <X className="w-5 h-5" />
            </button>
          </div>
        </div>

        <div className="space-y-8 p-6 overflow-y-auto min-h-0">
          {isLoading ? (
            <div className="py-12 flex justify-center text-slate-400">
              Loading details...
            </div>
          ) : !pr ? (
            <div className="py-12 flex justify-center text-rose-500">
              Failed to load PR
            </div>
          ) : (
            <div className="space-y-8">
              <div>
                <h3 className="text-sm font-bold text-slate-400 uppercase tracking-wider mb-2">
                  Request Reason
                </h3>
                <p className="text-slate-700 bg-slate-50 p-4 rounded-xl border border-slate-100">
                  {pr.reason || "No reason provided."}
                </p>
              </div>

              <div>
                <h3 className="text-sm font-bold text-slate-400 uppercase tracking-wider mb-3">
                  Requested Items
                </h3>
                <div className="table-container">
                  <table className="w-full text-left responsive-table">
                    <thead className="bg-slate-50 border-b border-slate-200">
                      <tr>
                        <th className="px-4 py-3 text-xs font-bold text-slate-500 uppercase">
                          Item
                        </th>
                        <th className="px-4 py-3 text-xs font-bold text-slate-500 uppercase">
                          Type
                        </th>
                        <th className="px-4 py-3 text-xs font-bold text-slate-500 uppercase">
                          Qty
                        </th>
                        <th className="px-4 py-3 text-xs font-bold text-slate-500 uppercase">
                          Est. Cost
                        </th>
                        <th className="px-4 py-3 text-xs font-bold text-slate-500 uppercase">
                          Justification
                        </th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-slate-100">
                      {pr.items?.map((item: any) => (
                        <tr key={item.id} className="table-row">
                          <td data-label="Item" className="table-cell text-sm font-medium text-slate-800">
                            {item.name || `Item #${item.item_id || item.asset_id}`}
                          </td>
                          <td data-label="Type" className="table-cell text-sm text-slate-600">
                            {item.item_type === 'asset' ? 'Asset' : 'Inventory'}
                          </td>
                          <td data-label="Qty" className="table-cell text-sm text-slate-600">
                            {item.quantity}
                          </td>
                          <td data-label="Est. Cost" className="table-cell text-sm text-slate-600">
                            KES {item.estimated_cost?.toLocaleString()}
                          </td>
                          <td data-label="Justification" className="table-cell text-sm text-slate-500 max-w-xs truncate" title={item.justification}>
                            {item.justification || "—"}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            </div>
          )}
        </div>

        <div className="flex justify-end p-6 border-t border-slate-100 bg-slate-50/60">
          <button className="btn-secondary" onClick={onClose}>
            Close
          </button>
        </div>
      </div>
    </Modal>
  );
}
