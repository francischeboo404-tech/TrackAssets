import React, { useState } from 'react';
import { Package, Hash, FileText, ChevronUp, ChevronDown, Warehouse } from 'lucide-react';
import { Modal } from './Modal';
import { useUpdateStock } from '../../hooks/useInventory';
import { useWarehouses } from '../../hooks/useWarehouses';

interface StockAdjustmentModalProps {
  isOpen: boolean;
  onClose: () => void;
  item: any;
  initialType?: 'IN' | 'OUT';
}

export const StockAdjustmentModal: React.FC<StockAdjustmentModalProps> = ({ isOpen, onClose, item, initialType = 'IN' }) => {
  const [quantity, setQuantity] = useState(1);
  const [type, setType] = useState<'IN' | 'OUT'>(initialType);
  const [warehouseId, setWarehouseId] = useState<number | undefined>(undefined);
  const [reference, setReference] = useState('');
  const [notes, setNotes] = useState('');
  const updateStock = useUpdateStock();
  const { data: warehouses } = useWarehouses();

  // Reset type when modal opens with a specific initialType
  React.useEffect(() => {
    if (isOpen) {
      setType(initialType);
      setWarehouseId(undefined);
    }
  }, [isOpen, initialType]);

  const handleAdjust = () => {
    updateStock.mutate({
      id: item.id,
      quantity,
      type,
      reference,
      notes,
      warehouse_id: warehouseId,
    }, {
      onSuccess: () => {
        onClose();
        setQuantity(1);
        setWarehouseId(undefined);
        setReference('');
        setNotes('');
      }
    });
  };

  return (
    <Modal
      isOpen={isOpen}
      onClose={onClose}
      title={`${type === 'IN' ? 'Restock' : 'Remove Stock'}: ${item?.name}`}
      footer={
        <>
          <button onClick={onClose} className="px-4 py-2 text-slate-600 font-semibold hover:bg-slate-100 rounded-lg transition-colors">
            Cancel
          </button>
          <button 
            onClick={handleAdjust}
            disabled={updateStock.isPending || !reference || !warehouseId}
            className="btn-primary flex items-center gap-2 disabled:opacity-50"
          >
            {updateStock.isPending ? 'Processing...' : 'Confirm Adjustment'}
          </button>
        </>
      }
    >
      <div className="space-y-6">
        <div className="grid grid-cols-2 gap-4">
          <button 
            onClick={() => setType('IN')}
            className={`p-4 rounded-xl border-2 transition-all flex flex-col items-center gap-2 ${type === 'IN' ? 'border-indigo-600 bg-indigo-50 text-indigo-700' : 'border-slate-100 bg-slate-50 text-slate-400 hover:border-slate-200'}`}
          >
            <ChevronUp className="w-6 h-6" />
            <span className="font-bold">Stock In</span>
          </button>
          <button 
            onClick={() => setType('OUT')}
            className={`p-4 rounded-xl border-2 transition-all flex flex-col items-center gap-2 ${type === 'OUT' ? 'border-rose-600 bg-rose-50 text-rose-700' : 'border-slate-100 bg-slate-50 text-slate-400 hover:border-slate-200'}`}
          >
            <ChevronDown className="w-6 h-6" />
            <span className="font-bold">Stock Out</span>
          </button>
        </div>

        <div className="space-y-2">
          <label className="text-sm font-bold text-slate-700 flex items-center gap-2 italic">
            <Warehouse className="w-4 h-4 text-brand-primary" /> Target Facility / Warehouse (Required)
          </label>
          <select
            value={warehouseId || ''}
            onChange={(e) => setWarehouseId(e.target.value ? Number(e.target.value) : undefined)}
            className="w-full bg-white border border-slate-200 rounded-xl py-3 px-4 text-sm focus:ring-2 focus:ring-indigo-500/20 focus:border-indigo-500 transition-all outline-none cursor-pointer"
            style={{ fontFamily: 'Outfit' }}
          >
            <option value="">Select a warehouse facility...</option>
            {warehouses?.map((wh) => (
              <option key={wh.warehouse_id} value={wh.warehouse_id}>
                {wh.warehouse_name}
              </option>
            ))}
          </select>
        </div>

        <div className="space-y-2">
          <label className="text-sm font-bold text-slate-700 flex items-center gap-2 italic">
            <Package className="w-4 h-4 text-brand-primary" /> Adjustment Quantity
          </label>
          <div className="flex items-center gap-4 bg-slate-100 p-2 rounded-xl border border-slate-200">
            <button onClick={() => setQuantity(q => Math.max(1, q - 1))} className="w-10 h-10 flex items-center justify-center bg-white rounded-lg shadow-sm font-bold text-slate-600 hover:text-indigo-600 transition-colors">-</button>
            <input 
              type="number" 
              value={quantity}
              onChange={(e) => setQuantity(parseInt(e.target.value) || 1)}
              className="flex-1 bg-transparent border-none text-center font-bold text-xl outline-none"
            />
            <button onClick={() => setQuantity(q => q + 1)} className="w-10 h-10 flex items-center justify-center bg-white rounded-lg shadow-sm font-bold text-slate-600 hover:text-indigo-600 transition-colors">+</button>
          </div>
        </div>

        <div className="space-y-2">
          <label className="text-sm font-bold text-slate-700 flex items-center gap-2 italic">
            <Hash className="w-4 h-4 text-brand-primary" /> Reference # (Required)
          </label>
          <input 
            type="text" 
            placeholder="e.g. PO-12345 or Invoice ID"
            value={reference}
            onChange={(e) => setReference(e.target.value)}
            className="w-full bg-white border border-slate-200 rounded-xl py-3 px-4 text-sm focus:ring-2 focus:ring-indigo-500/20 focus:border-indigo-500 transition-all outline-none"
          />
        </div>

        <div className="space-y-2">
          <label className="text-sm font-bold text-slate-700 flex items-center gap-2 italic">
            <FileText className="w-4 h-4 text-brand-primary" /> Transaction Notes
          </label>
          <textarea 
            placeholder="Reason for adjustment..."
            rows={3}
            value={notes}
            onChange={(e) => setNotes(e.target.value)}
            className="w-full bg-white border border-slate-200 rounded-xl py-3 px-4 text-sm focus:ring-2 focus:ring-indigo-500/20 focus:border-indigo-500 transition-all outline-none resize-none"
          />
        </div>
      </div>
    </Modal>
  );
};
