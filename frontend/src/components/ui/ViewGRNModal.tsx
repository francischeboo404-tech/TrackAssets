import React from 'react';
import { useQuery } from '@tanstack/react-query';
import api from '../../services/api';
import { Modal } from './Modal';
import { PackageOpen } from 'lucide-react';

interface ViewGRNModalProps {
  isOpen: boolean;
  onClose: () => void;
  grnId: number | null;
}

export default function ViewGRNModal({ isOpen, onClose, grnId }: ViewGRNModalProps) {
  const { data: grn, isLoading } = useQuery({
    queryKey: ['goodsReceipt', grnId],
    queryFn: async () => {
      if (!grnId) return null;
      const res = await api.get(`/receiving/goods-receipts/${grnId}`);
      return res.data;
    },
    enabled: !!grnId,
  });

  return (
    <Modal isOpen={isOpen} onClose={onClose} title={grn?.grn_number || 'Loading GRN...'} size="2xl">
      <div className="space-y-8">
        {isLoading ? (
          <div className="py-12 flex justify-center text-slate-400">Loading details...</div>
        ) : !grn ? (
          <div className="py-12 flex justify-center text-rose-500">Failed to load GRN</div>
        ) : (
          <div className="space-y-8">
            <div className="flex items-center justify-between flex-wrap gap-4">
              <div>
                <p className="text-sm text-slate-500 font-medium">
                  Total Items Received: {grn.total_quantity || 0}
                </p>
              </div>
              <span className={`inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-bold uppercase tracking-wider ${
                grn.status === 'approved' ? 'bg-emerald-100 text-emerald-700' :
                grn.status === 'rejected' ? 'bg-rose-100 text-rose-700' :
                'bg-amber-100 text-amber-700'
              }`}>
                {grn.status}
              </span>
            </div>

            <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
              <div className="bg-slate-50 p-4 rounded-xl border border-slate-100">
                <p className="text-xs font-bold text-slate-400 uppercase">Received Date</p>
                <p className="text-lg font-bold text-slate-800 mt-1">{new Date(grn.received_date).toLocaleDateString()}</p>
              </div>
              <div className="bg-slate-50 p-4 rounded-xl border border-slate-100">
                <p className="text-xs font-bold text-slate-400 uppercase">Linked PO ID</p>
                <p className="text-lg font-bold text-slate-800 mt-1">PO-{grn.po_id}</p>
              </div>
              <div className="bg-slate-50 p-4 rounded-xl border border-slate-100">
                <p className="text-xs font-bold text-slate-400 uppercase">Invoice No.</p>
                <p className="text-lg font-bold text-slate-800 mt-1">{grn.invoice_number || '—'}</p>
              </div>
              <div className="bg-slate-50 p-4 rounded-xl border border-slate-100">
                <p className="text-xs font-bold text-slate-400 uppercase">Delivery Note</p>
                <p className="text-lg font-bold text-slate-800 mt-1">{grn.delivery_note_number || '—'}</p>
              </div>
              {grn.inspection_report && (
                <div className="bg-slate-50 p-4 rounded-xl border border-slate-100 md:col-span-4 flex items-center justify-between">
                  <div>
                    <p className="text-xs font-bold text-slate-400 uppercase">Inspection Report</p>
                    <p className="text-lg font-bold text-slate-800 mt-1">{grn.inspection_report.iar_number}</p>
                  </div>
                  <span className="text-sm font-bold text-slate-500 uppercase tracking-wider">{grn.inspection_report.status}</span>
                </div>
              )}
            </div>

            <div>
              <h3 className="text-sm font-bold text-slate-400 uppercase tracking-wider mb-3">Received Items</h3>
              <div className="table-container">
                <table className="w-full text-left responsive-table">
                  <thead className="bg-slate-50 border-b border-slate-200">
                    <tr>
                      <th className="px-4 py-3 text-xs font-bold text-slate-500 uppercase">Item</th>
                      <th className="px-4 py-3 text-xs font-bold text-slate-500 uppercase">Received</th>
                      <th className="px-4 py-3 text-xs font-bold text-emerald-600 uppercase">Accepted</th>
                      <th className="px-4 py-3 text-xs font-bold text-rose-600 uppercase">Rejected</th>
                      <th className="px-4 py-3 text-xs font-bold text-slate-500 uppercase text-right">Unit Cost</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-100">
                    {grn.items?.map((item: any) => (
                      <tr key={item.id} className="hover:bg-slate-50 table-row">
                        <td data-label="Item" className="table-cell px-4 py-3 text-sm font-medium text-slate-800">{item.name || `Item #${item.item_id}`}</td>
                        <td data-label="Received" className="table-cell px-4 py-3 text-sm text-slate-600">{item.quantity_received}</td>
                        <td data-label="Accepted" className="table-cell px-4 py-3 text-sm font-bold text-emerald-600">{item.quantity_accepted}</td>
                        <td data-label="Rejected" className="table-cell px-4 py-3 text-sm font-bold text-rose-600">{item.quantity_rejected}</td>
                        <td data-label="Unit Cost" className="table-cell px-4 py-3 text-sm font-medium text-slate-800 md:text-right">KES {item.unit_cost?.toLocaleString()}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          </div>
        )}
      </div>
    </Modal>
  );
}
