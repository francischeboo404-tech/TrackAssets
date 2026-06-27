import React from 'react';
import { useQuery } from '@tanstack/react-query';
import api from '../../services/api';
import { Modal } from './Modal';
import { ClipboardList, CheckCircle2, Clock, XCircle } from 'lucide-react';

interface ViewRISModalProps {
  isOpen: boolean;
  onClose: () => void;
  risId: number | null;
}

export default function ViewRISModal({ isOpen, onClose, risId }: ViewRISModalProps) {
  const { data: ris, isLoading } = useQuery({
    queryKey: ['requisition', risId],
    queryFn: async () => {
      if (!risId) return null;
      const res = await api.get(`/requisition/issue-slips/${risId}`);
      return res.data;
    },
    enabled: !!risId,
  });

  return (
    <Modal isOpen={isOpen} onClose={onClose} title={ris?.ris_number || 'Loading RIS...'} size="2xl">
      <div className="space-y-6">
        {isLoading ? (
          <div className="py-12 flex justify-center text-slate-400">Loading details...</div>
        ) : !ris ? (
          <div className="py-12 flex justify-center text-rose-500">Failed to load Requisition Slip</div>
        ) : (
          <div className="space-y-8">
            <div className="flex items-center justify-between flex-wrap gap-4">
              <div>
                <p className="text-sm text-slate-500 font-medium">
                  Requisition Slip details
                </p>
              </div>
              <span className={`inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-bold uppercase tracking-wider ${
                ris.status === 'issued' ? 'bg-emerald-100 text-emerald-700' :
                ris.status === 'approved' ? 'bg-blue-100 text-blue-700' :
                ris.status === 'rejected' ? 'bg-rose-100 text-rose-700' :
                'bg-amber-100 text-amber-700'
              }`}>
                {ris.status === 'issued' && <CheckCircle2 className="w-4 h-4" />}
                {ris.status === 'approved' && <CheckCircle2 className="w-4 h-4" />}
                {ris.status === 'rejected' && <XCircle className="w-4 h-4" />}
                {ris.status === 'pending' && <Clock className="w-4 h-4" />}
                {ris.status}
              </span>
            </div>

            <div>
              <h3 className="text-sm font-bold text-slate-400 uppercase tracking-wider mb-3">Requested Items</h3>
              <div className="table-container">
                <table className="w-full text-left responsive-table">
                  <thead className="bg-slate-50 border-b border-slate-200">
                    <tr>
                      <th className="px-4 py-3 text-xs font-bold text-slate-500 uppercase">Item</th>
                      <th className="px-4 py-3 text-xs font-bold text-slate-500 uppercase">Requested Qty</th>
                      <th className="px-4 py-3 text-xs font-bold text-emerald-600 uppercase">Issued Qty</th>
                      <th className="px-4 py-3 text-xs font-bold text-slate-500 uppercase">Unit Cost</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-100">
                    {ris.items?.map((item: any) => (
                      <tr key={item.id} className="hover:bg-slate-50 table-row">
                        <td data-label="Item" className="table-cell px-4 py-3 text-sm font-medium text-slate-800">{item.name || `Item #${item.item_id}`}</td>
                        <td data-label="Requested Qty" className="table-cell px-4 py-3 text-sm text-slate-600">{item.quantity_requested}</td>
                        <td data-label="Issued Qty" className="table-cell px-4 py-3 text-sm font-bold text-emerald-600">{item.quantity_issued}</td>
                        <td data-label="Unit Cost" className="table-cell px-4 py-3 text-sm text-slate-600">KES {item.unit_cost?.toLocaleString() || '—'}</td>
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
