import React from 'react';
import { useQuery } from '@tanstack/react-query';
import api from '../../services/api';
import { Modal } from './Modal';
import { FileText } from 'lucide-react';
import CloseCanvassButton from './CloseCanvassButton';

interface ViewPOModalProps {
  isOpen: boolean;
  onClose: () => void;
  poId: number | null;
}

export default function ViewPOModal({ isOpen, onClose, poId }: ViewPOModalProps) {
  const { data: po, isLoading } = useQuery({
    queryKey: ['purchaseOrder', poId],
    queryFn: async () => {
      if (!poId) return null;
      const res = await api.get(`/procurement/purchase-orders/${poId}`);
      return res.data;
    },
    enabled: !!poId,
  });

  return (
    <Modal isOpen={isOpen} onClose={onClose} title={po?.po_number || 'Loading PO...'} size="2xl">
      <div className="space-y-8">
        {isLoading ? (
          <div className="py-12 flex justify-center text-slate-400">Loading details...</div>
        ) : !po ? (
          <div className="py-12 flex justify-center text-rose-500">Failed to load PO</div>
        ) : (
          <div className="space-y-8">
            <div className="flex items-center justify-between flex-wrap gap-4">
              <div>
                <p className="text-sm text-slate-500 font-medium">
                  Supplier: <span className="text-slate-700">{po.supplier_name}</span>
                </p>
              </div>
              <span className={`inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-bold uppercase tracking-wider ${
                po.status === 'approved' || po.status === 'received' ? 'bg-emerald-100 text-emerald-700' :
                po.status === 'rejected' || po.status === 'cancelled' ? 'bg-rose-100 text-rose-700' :
                'bg-amber-100 text-amber-700'
              }`}>
                {po.status}
              </span>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              <div className="bg-slate-50 p-4 rounded-xl border border-slate-100">
                <p className="text-xs font-bold text-slate-400 uppercase">Total Amount</p>
                <p className="text-lg font-bold text-slate-800 mt-1">KES {po.total_amount?.toLocaleString()}</p>
              </div>
              <div className="bg-slate-50 p-4 rounded-xl border border-slate-100">
                <p className="text-xs font-bold text-slate-400 uppercase">Created Date</p>
                <p className="text-lg font-bold text-slate-800 mt-1">{new Date(po.created_at).toLocaleDateString()}</p>
              </div>
              <div className="bg-slate-50 p-4 rounded-xl border border-slate-100">
                <p className="text-xs font-bold text-slate-400 uppercase">Linked PR ID</p>
                <p className="text-lg font-bold text-slate-800 mt-1">{po.pr_id || 'N/A'}</p>
              </div>
            </div>

            <div>
              <h3 className="text-sm font-bold text-slate-400 uppercase tracking-wider mb-3">Order Items</h3>
              <div className="table-container">
                <table className="w-full text-left responsive-table">
                  <thead className="bg-slate-50 border-b border-slate-200">
                    <tr>
                      <th className="px-4 py-3 text-xs font-bold text-slate-500 uppercase">Item</th>
                      <th className="px-4 py-3 text-xs font-bold text-slate-500 uppercase">Qty</th>
                      <th className="px-4 py-3 text-xs font-bold text-slate-500 uppercase">Unit Cost (KES)</th>
                      <th className="px-4 py-3 text-xs font-bold text-slate-500 uppercase text-right">Total Cost</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-100">
                    {po.items?.map((item: any) => (
                      <tr key={item.id} className="hover:bg-slate-50 table-row">
                        <td data-label="Item" className="table-cell px-4 py-3 text-sm font-medium text-slate-800">{item.name || `Item #${item.item_id}`}</td>
                        <td data-label="Qty" className="table-cell px-4 py-3 text-sm text-slate-600">{item.quantity}</td>
                        <td data-label="Unit Cost" className="table-cell px-4 py-3 text-sm text-slate-600">{item.unit_cost?.toLocaleString()}</td>
                        <td data-label="Total Cost" className="table-cell px-4 py-3 text-sm font-medium text-slate-800 md:text-right">{item.total_cost?.toLocaleString()}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>

            {po.canvass_quotes && po.canvass_quotes.length > 0 && (
              <div>
                <h3 className="text-sm font-bold text-slate-400 uppercase tracking-wider mb-3">Canvass Quotes</h3>
                <div className="flex flex-wrap gap-4">
                  {po.canvass_quotes.map((q: any) => (
                    <div key={q.id} className="w-full sm:w-auto border border-slate-200 p-4 rounded-xl">
                      <p className="font-bold text-slate-800">{q.supplier_name}</p>
                      <p className="text-sm text-slate-500 mt-1">{q.item_name}</p>
                      <p className="text-emerald-600 font-bold mt-2">KES {q.unit_cost?.toLocaleString()}</p>
                      {q.is_active !== false && (
                        <div className="mt-3">
                          <CloseCanvassButton poId={po.id} quoteId={q.id} />
                        </div>
                      )}
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        )}
      </div>
    </Modal>
  );
}
