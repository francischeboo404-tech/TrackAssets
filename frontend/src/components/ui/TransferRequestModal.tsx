import React, { useState } from 'react';
import { Modal } from './Modal';
import { ArrowRightLeft, MapPin, MessageSquare, Building2, Loader2 } from 'lucide-react';
import { useRequestTransfer } from '../../hooks/useTransfers';
import { useWarehouses, useWarehouseDetails } from '../../hooks/useWarehouses';
import { useDepartments } from '../../hooks/useDepartments';
import { useToast } from '../../context/ToastContext';

interface TransferRequestModalProps {
  isOpen: boolean;
  onClose: () => void;
  asset?: any | null;
  inventoryItem?: any | null;
  itemType?: 'asset' | 'inventory';
}

export const TransferRequestModal: React.FC<TransferRequestModalProps> = ({ isOpen, onClose, asset, inventoryItem, itemType = 'asset' }) => {
  const [newDepartmentId, setNewDepartmentId] = useState('');
  const [newLocation, setNewLocation] = useState('');
  const [toWarehouseId, setToWarehouseId] = useState('');
  const [toBinId, setToBinId] = useState('');
  const [comment, setComment] = useState('');
  const [quantity, setQuantity] = useState<number>(1);
  
  const { data: departments } = useDepartments();
  const { data: warehouses } = useWarehouses();
  const { data: bins } = useWarehouseDetails(Number(toWarehouseId));
  const { mutate: requestTransfer, isPending } = useRequestTransfer();
  const { addToast } = useToast();

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!newDepartmentId) return;

    const payload: any = { 
      new_department_id: Number(newDepartmentId), 
      new_location: newLocation, 
      comment,
      to_warehouse_id: toWarehouseId ? Number(toWarehouseId) : undefined,
      to_bin_id: toBinId ? Number(toBinId) : undefined,
      item_type: itemType
    };

    if (itemType === 'asset' && asset) {
      payload.asset_id = asset.id;
    } else if (itemType === 'inventory' && inventoryItem) {
      payload.inventory_item_id = inventoryItem.id;
      payload.quantity = Number(quantity);
    } else {
      return;
    }

    requestTransfer(
      payload,
      {
        onSuccess: () => {
          const itemName = itemType === 'asset' ? asset.name : inventoryItem.name;
          addToast('success', 'Transfer Requested', `Movement request for ${itemName} has been submitted.`);
          onClose();
          setNewDepartmentId('');
          setNewLocation('');
          setToWarehouseId('');
          setToBinId('');
          setComment('');
          setQuantity(1);
        },
        onError: (error: any) => {
          addToast('error', 'Request Failed', error.response?.data?.message || 'Failed to submit transfer request.');
        }
      }
    );
  };

  if (!asset && !inventoryItem) return null;

  return (
    <Modal isOpen={isOpen} onClose={onClose} title="Request Asset Transfer">
      <form onSubmit={handleSubmit} className="space-y-6">
        
        <div className="bg-slate-50 p-4 rounded-xl border border-slate-200">
          <div className="flex items-center gap-3 mb-2">
            <div className="p-2 bg-white rounded-lg shadow-sm">
              <ArrowRightLeft className="w-5 h-5 text-brand-primary" />
            </div>
            <div>
              <h4 className="font-bold text-slate-900">{itemType === 'asset' ? asset?.name : inventoryItem?.name}</h4>
              <p className="text-xs font-mono text-slate-500">{itemType === 'asset' ? asset?.asset_code : inventoryItem?.sku}</p>
            </div>
          </div>
          {itemType === 'asset' && (
            <div className="flex gap-4 text-xs text-slate-600 mt-3 pt-3 border-t border-slate-200">
              <div><span className="font-bold">Current Dept:</span> {asset?.department_name}</div>
              <div><span className="font-bold">Location:</span> {asset?.location || 'Unassigned'}</div>
            </div>
          )}
          {itemType === 'inventory' && (
            <div className="flex gap-4 text-xs text-slate-600 mt-3 pt-3 border-t border-slate-200">
              <div><span className="font-bold">Global Stock:</span> {inventoryItem?.quantity} {inventoryItem?.unit}</div>
            </div>
          )}
        </div>

        {itemType === 'inventory' && (
          <div>
            <label className="block text-sm font-bold text-slate-700 mb-1.5 uppercase tracking-wide">Quantity to Transfer</label>
            <div className="relative">
              <input
                type="number"
                min="1"
                max={inventoryItem?.quantity}
                value={quantity}
                onChange={(e) => setQuantity(Number(e.target.value))}
                className="w-full bg-white border border-slate-200 text-slate-900 rounded-xl py-2.5 px-4 focus:ring-2 focus:ring-brand-primary/20 focus:border-brand-primary transition-all outline-none"
              />
            </div>
          </div>
        )}

        <div className="space-y-4">
          <div>
            <label className="block text-sm font-bold text-slate-700 mb-1.5 uppercase tracking-wide">Destination Department</label>
            <div className="relative">
              <Building2 className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-slate-400" />
              <select
                required
                value={newDepartmentId}
                onChange={(e) => setNewDepartmentId(e.target.value)}
                className="w-full bg-white border border-slate-200 text-slate-900 rounded-xl py-2.5 pl-10 pr-4 focus:ring-2 focus:ring-brand-primary/20 focus:border-brand-primary transition-all outline-none appearance-none"
              >
                <option value="">Select Department...</option>
                {departments?.filter((d: any) => d.id !== asset.department_id).map((dept: any) => (
                  <option key={dept.id} value={dept.id}>{dept.name} ({dept.code})</option>
                ))}
              </select>
            </div>
          </div>
          
          <div>
            <label className="block text-sm font-bold text-slate-700 mb-1.5 uppercase tracking-wide">Destination Warehouse (Optional)</label>
            <div className="relative">
              <Building2 className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-slate-400" />
              <select
                value={toWarehouseId}
                onChange={(e) => { setToWarehouseId(e.target.value); setToBinId(''); }}
                className="w-full bg-white border border-slate-200 text-slate-900 rounded-xl py-2.5 pl-10 pr-4 focus:ring-2 focus:ring-brand-primary/20 focus:border-brand-primary transition-all outline-none appearance-none"
              >
                <option value="">Select Warehouse...</option>
                {warehouses?.map((wh: any) => (
                  <option key={wh.id || wh.warehouse_id} value={wh.id || wh.warehouse_id}>{wh.name || wh.warehouse_name}</option>
                ))}
              </select>
            </div>
          </div>

          <div>
            <label className="block text-sm font-bold text-slate-700 mb-1.5 uppercase tracking-wide">Destination Bin (Optional)</label>
            <div className="relative">
              <MapPin className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-slate-400" />
              <select
                value={toBinId}
                onChange={(e) => setToBinId(e.target.value)}
                disabled={!toWarehouseId}
                className="w-full bg-white border border-slate-200 text-slate-900 rounded-xl py-2.5 pl-10 pr-4 focus:ring-2 focus:ring-brand-primary/20 focus:border-brand-primary transition-all outline-none appearance-none disabled:opacity-50"
              >
                <option value="">Select Bin...</option>
                {bins?.map((bin: any) => (
                  <option key={bin.id} value={bin.id}>{bin.code} {bin.description ? `- ${bin.description}` : ''}</option>
                ))}
              </select>
            </div>
          </div>

          <div>
            <label className="block text-sm font-bold text-slate-700 mb-1.5 uppercase tracking-wide">New Location String (Optional)</label>
            <div className="relative">
              <MapPin className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-slate-400" />
              <input
                type="text"
                value={newLocation}
                onChange={(e) => setNewLocation(e.target.value)}
                placeholder="e.g. Floor 3, Zone D"
                className="w-full bg-white border border-slate-200 text-slate-900 rounded-xl py-2.5 pl-10 pr-4 focus:ring-2 focus:ring-brand-primary/20 focus:border-brand-primary transition-all outline-none"
              />
            </div>
          </div>

          <div>
            <label className="block text-sm font-bold text-slate-700 mb-1.5 uppercase tracking-wide">Reason for Transfer</label>
            <div className="relative">
              <MessageSquare className="absolute left-3 top-3 w-5 h-5 text-slate-400" />
              <textarea
                value={comment}
                onChange={(e) => setComment(e.target.value)}
                placeholder="Please explain why this asset is being moved..."
                rows={3}
                className="w-full bg-white border border-slate-200 text-slate-900 rounded-xl py-2.5 pl-10 pr-4 focus:ring-2 focus:ring-brand-primary/20 focus:border-brand-primary transition-all outline-none resize-none"
              />
            </div>
          </div>
        </div>

        <div className="flex gap-3 pt-4 border-t border-slate-100">
          <button
            type="button"
            onClick={onClose}
            className="flex-1 px-4 py-2.5 border border-slate-200 text-slate-600 font-bold rounded-xl hover:bg-slate-50 transition-colors"
          >
            Cancel
          </button>
          <button
            type="submit"
            disabled={isPending || !newDepartmentId}
            className="flex-1 btn-primary flex justify-center items-center gap-2"
          >
            {isPending ? (
              <Loader2 className="w-5 h-5 animate-spin" />
            ) : (
              'Submit Request'
            )}
          </button>
        </div>
      </form>
    </Modal>
  );
};
