import React from 'react';
import { useQuery } from '@tanstack/react-query';
import api from '../../services/api';

interface POCanvassFormProps {
  poId: number;
  suppliers: any[];
  onSave: (payload: { supplier_id?: number; item_id?: number; supplier_name?: string; item_name?: string; unit_cost: number }) => void;
  onCancel: () => void;
}

export default function POCanvassForm({ poId, suppliers, onSave, onCancel }: POCanvassFormProps) {
  const { data: po, isLoading } = useQuery({
    queryKey: ['purchaseOrder', poId],
    queryFn: async () => {
      const res = await api.get(`/procurement/purchase-orders/${poId}`);
      return res.data;
    },
    enabled: !!poId,
  });

  const items = po?.items || [];

  const [supplierId, setSupplierId] = React.useState('');
  const [itemId, setItemId] = React.useState('');
  const [unitCost, setUnitCost] = React.useState('');

  return (
    <div>
      <div className="mb-3">
        <label className="text-xs font-medium text-slate-500">Supplier</label>
        <select
          className="input-field w-full"
          value={supplierId}
          onChange={(e) => setSupplierId(e.target.value)}
        >
          <option value="">-- Select Supplier --</option>
          {suppliers?.map((s: any) => (
            <option key={s.id} value={s.id}>{s.name || `Supplier #${s.id}`}</option>
          ))}
        </select>
      </div>

      <div className="mb-3">
        <label className="text-xs font-medium text-slate-500">Item</label>
        <select
          className="input-field w-full"
          value={itemId}
          onChange={(e) => setItemId(e.target.value)}
        >
          <option value="">-- Select Item --</option>
          {items.map((it: any) => (
            <option key={it.id} value={it.item_id}>{it.name || `Item #${it.item_id}`}</option>
          ))}
        </select>
      </div>

      <div className="mb-4">
        <label className="text-xs font-medium text-slate-500">Unit Cost (KES)</label>
        <input
          type="number"
          min="0"
          step="0.01"
          required
          className="input-field w-full"
          value={unitCost}
          onChange={(e) => setUnitCost(e.target.value)}
        />
      </div>

      <div className="flex justify-end gap-3">
        <button type="button" className="btn-secondary" onClick={onCancel}>Cancel</button>
        <button
          type="button"
          className="btn-primary"
          onClick={() => {
            if (!supplierId || !itemId || unitCost.trim() === '') {
              return;
            }
            onSave({
              supplier_id: Number(supplierId),
              item_id: Number(itemId),
              supplier_name: suppliers?.find((s: any) => String(s.id) === supplierId)?.name,
              item_name: items.find((it: any) => String(it.item_id) === itemId)?.name,
              unit_cost: Number(unitCost),
            });
          }}
        >
          Save Quote
        </button>
      </div>
    </div>
  );
}
