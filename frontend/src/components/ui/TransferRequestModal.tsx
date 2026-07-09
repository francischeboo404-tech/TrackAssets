import React, { useEffect, useMemo, useState } from 'react';
import { Modal } from './Modal';
import { ArrowRightLeft, MapPin, MessageSquare, Building2, Loader2, AlertCircle } from 'lucide-react';
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
  const [fromDepartmentId, setFromDepartmentId] = useState('');
  const [newLocation, setNewLocation] = useState('');
  const [fromWarehouseId, setFromWarehouseId] = useState('');
  const [toWarehouseId, setToWarehouseId] = useState('');
  const [toBinId, setToBinId] = useState('');
  const [comment, setComment] = useState('');
  const [quantity, setQuantity] = useState<number>(1);
  
  const { data: departments } = useDepartments();
  const { data: warehouses } = useWarehouses();
  const { data: bins } = useWarehouseDetails(Number(toWarehouseId));
  const { mutate: requestTransfer, isPending } = useRequestTransfer();
  const { addToast } = useToast();

  const currentDepartmentId = asset?.department_id;
  const selectedDestinationDepartment = useMemo(
    () => departments?.find((dept: any) => dept.id === Number(newDepartmentId)),
    [departments, newDepartmentId],
  );
  const destinationDepartmentWarehouseId = selectedDestinationDepartment?.warehouse_id;
  const [warehouseMessage, setWarehouseMessage] = useState<string | null>(null);

  useEffect(() => {
    if (!destinationDepartmentWarehouseId) {
      setWarehouseMessage(null);
      return;
    }

    if (toWarehouseId && Number(toWarehouseId) !== destinationDepartmentWarehouseId) {
      setWarehouseMessage(
        'Selected destination department is linked to a different warehouse. Leave warehouse empty to use the department warehouse or choose the correct warehouse.'
      );
    } else {
      setWarehouseMessage(
        `Destination department is linked to warehouse ${destinationDepartmentWarehouseId}. This warehouse will be used for the transfer.`
      );
    }
  }, [destinationDepartmentWarehouseId, toWarehouseId]);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!newDepartmentId) return;

    const payload: any = {
      transfer_type: 'department_to_department',
      new_department_id: Number(newDepartmentId),
      from_department_id: fromDepartmentId ? Number(fromDepartmentId) : undefined,
      from_warehouse_id: fromWarehouseId ? Number(fromWarehouseId) : undefined,
      new_location: newLocation,
      comment,
      to_warehouse_id: toWarehouseId ? Number(toWarehouseId) : undefined,
      to_bin_id: toBinId ? Number(toBinId) : undefined,
      item_type: itemType,
    };

    // If destination department is linked to a warehouse, enforce alignment on client side
    if (destinationDepartmentWarehouseId) {
      // if user somehow selected a different warehouse, treat as validation error
      if (toWarehouseId && Number(toWarehouseId) !== destinationDepartmentWarehouseId) {
        addToast('error', 'Validation Error', 'Selected destination department is linked to a different warehouse. Leave warehouse empty to use the department warehouse or choose the correct warehouse.');
        return;
      }
      // ensure payload includes the department's warehouse id so server can validate/record it
      payload.to_warehouse_id = destinationDepartmentWarehouseId;
    }

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
          setFromDepartmentId('');
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
    <Modal isOpen={isOpen} onClose={onClose} title={itemType === 'inventory' ? 'Request Inventory Transfer' : 'Request Asset Transfer'}>
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
          {itemType === 'inventory' && (
            <>
              <div>
                <label className="block text-sm font-bold text-slate-700 mb-1.5 uppercase tracking-wide">Source Department (Optional)</label>
                <div className="relative">
                  <Building2 className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-slate-400" />
                  <select
                    value={fromDepartmentId}
                    onChange={(e) => setFromDepartmentId(e.target.value)}
                    className="w-full bg-white border border-slate-200 text-slate-900 rounded-xl py-2.5 pl-10 pr-4 focus:ring-2 focus:ring-brand-primary/20 focus:border-brand-primary transition-all outline-none appearance-none"
                  >
                    <option value="">Select Source Department...</option>
                    {departments?.map((dept: any) => (
                      <option key={dept.id} value={dept.id}>
                        {dept.name} ({dept.code})
                      </option>
                    ))}
                  </select>
                </div>
              </div>
              <div>
                <label className="block text-sm font-bold text-slate-700 mb-1.5 uppercase tracking-wide">Source Warehouse (Optional)</label>
                <div className="relative">
                  <Building2 className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-slate-400" />
                  <select
                    value={fromWarehouseId}
                    onChange={(e) => setFromWarehouseId(e.target.value)}
                    className="w-full bg-white border border-slate-200 text-slate-900 rounded-xl py-2.5 pl-10 pr-4 focus:ring-2 focus:ring-brand-primary/20 focus:border-brand-primary transition-all outline-none appearance-none"
                  >
                    <option value="">Select Source Warehouse...</option>
                    {warehouses?.map((wh: any) => (
                      <option key={wh.id || wh.warehouse_id} value={wh.id || wh.warehouse_id}>
                        {wh.name || wh.warehouse_name}
                      </option>
                    ))}
                  </select>
                </div>
                <p className="mt-2 text-xs text-slate-500">
                  Use this when the inventory transfer should originate from a specific warehouse source.
                </p>
              </div>
            </>
          )}

          <div>
            <label htmlFor="destination-department-select" className="block text-sm font-bold text-slate-700 mb-1.5 uppercase tracking-wide">Destination Department</label>
            <div className="relative">
              <Building2 className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-slate-400" />
              <select
                id="destination-department-select"
                required
                value={newDepartmentId}
                onChange={(e) => setNewDepartmentId(e.target.value)}
                className="w-full bg-white border border-slate-200 text-slate-900 rounded-xl py-2.5 pl-10 pr-4 focus:ring-2 focus:ring-brand-primary/20 focus:border-brand-primary transition-all outline-none appearance-none"
              >
                <option value="">Select Department...</option>
                {departments
                  ?.filter((d: any) => currentDepartmentId ? d.id !== currentDepartmentId : true)
                  .map((dept: any) => (
                    <option key={dept.id} value={dept.id}>
                      {dept.name} ({dept.code})
                    </option>
                  ))}
              </select>
            </div>
          </div>

          <div>
            <label htmlFor="destination-warehouse-select" className="block text-sm font-bold text-slate-700 mb-1.5 uppercase tracking-wide">Destination Warehouse (Optional)</label>
            {warehouseMessage && (
              <div
                aria-live="polite"
                className={`mb-3 rounded-xl border px-3 py-2.5 text-sm ${warehouseMessage.includes('different') ? 'border-rose-200 bg-rose-50 text-rose-700' : 'border-slate-200 bg-slate-50 text-slate-600'}`}
              >
                <div className="flex items-start gap-2">
                  <AlertCircle className="mt-0.5 h-4 w-4 shrink-0" />
                  <p>{warehouseMessage}</p>
                </div>
              </div>
            )}
            <div className="relative">
              <Building2 className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-slate-400" />
              <select
                id="destination-warehouse-select"
                value={toWarehouseId}
                disabled={Boolean(destinationDepartmentWarehouseId)}
                onChange={(e) => { setToWarehouseId(e.target.value); setToBinId(''); }}
                className="w-full bg-white border border-slate-200 text-slate-900 rounded-xl py-2.5 pl-10 pr-4 focus:ring-2 focus:ring-brand-primary/20 focus:border-brand-primary transition-all outline-none appearance-none disabled:opacity-70"
              >
                <option value="">Select Warehouse...</option>
                {warehouses?.map((wh: any) => (
                  <option key={wh.id || wh.warehouse_id} value={wh.id || wh.warehouse_id}>{wh.name || wh.warehouse_name}</option>
                ))}
              </select>
            </div>
            {warehouseMessage && (
              <p className={`mt-2 text-xs ${warehouseMessage.includes('different') ? 'text-rose-600' : 'text-slate-500'}`}>
                {warehouseMessage}
              </p>
            )}
          </div>

          <div>
            <label htmlFor="destination-bin-select" className="block text-sm font-bold text-slate-700 mb-1.5 uppercase tracking-wide">Destination Bin (Optional)</label>
            <div className="relative">
              <MapPin className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-slate-400" />
              <select
                id="destination-bin-select"
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
            {destinationDepartmentWarehouseId && (
              <p className="mt-2 text-xs text-slate-500">
                Destination department is linked to warehouse {destinationDepartmentWarehouseId}. Bin selection is restricted to that warehouse.
              </p>
            )}
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
