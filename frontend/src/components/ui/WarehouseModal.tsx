import React, { useState } from 'react';
import { X, Building2, MapPin, Hash, Loader2 } from 'lucide-react';
import { Modal } from './Modal';
import { useCreateWarehouse, useUpdateWarehouse } from '../../hooks/useWarehouses';
import { useToast } from '../../context/ToastContext';

interface WarehouseModalProps {
  isOpen: boolean;
  onClose: () => void;
  initialData?: { id: number; name: string; code: string; address?: string };
}

export const WarehouseModal: React.FC<WarehouseModalProps> = ({ isOpen, onClose, initialData }) => {
  const [name, setName] = useState(initialData?.name || '');
  const [code, setCode] = useState(initialData?.code || '');
  const [address, setAddress] = useState(initialData?.address || '');
  const { addToast } = useToast();
  
  // Update state when initialData changes
  React.useEffect(() => {
    if (isOpen) {
      setName(initialData?.name || '');
      setCode(initialData?.code || '');
      setAddress(initialData?.address || '');
    }
  }, [isOpen, initialData]);
  
  const { mutate: createWarehouse, isPending: isCreating } = useCreateWarehouse();
  const { mutate: updateWarehouse, isPending: isUpdating } = useUpdateWarehouse();

  const isPending = isCreating || isUpdating;

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!name || !code) return;

    if (initialData) {
      updateWarehouse(
        { id: initialData.id, data: { name, code, address } },
        {
          onSuccess: () => {
            addToast('success', 'Warehouse Updated', `Successfully updated ${name}`);
            onClose();
          },
          onError: (error: any) => {
            addToast('error', 'Update Failed', error.response?.data?.message || 'Failed to update warehouse');
          }
        }
      );
    } else {
      createWarehouse(
        { name, code, address },
        {
          onSuccess: () => {
            addToast('success', 'Warehouse Created', `Successfully created warehouse ${name}`);
            onClose();
            setName('');
            setCode('');
            setAddress('');
          },
          onError: (error: any) => {
            addToast('error', 'Creation Failed', error.response?.data?.message || 'Failed to create warehouse');
          }
        }
      );
    }
  };

  return (
    <Modal isOpen={isOpen} onClose={onClose} title={initialData ? "Edit Warehouse" : "Add New Warehouse"}>
      <form onSubmit={handleSubmit} className="space-y-6">
        <div className="space-y-4">
          <div>
            <label className="block text-sm font-bold text-slate-700 mb-1.5 uppercase tracking-wide">Warehouse Name</label>
            <div className="relative">
              <Building2 className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-slate-400" />
              <input
                type="text"
                required
                value={name}
                onChange={(e) => setName(e.target.value)}
                placeholder="e.g. Central Hub"
                className="w-full bg-slate-50 border border-slate-200 text-slate-900 rounded-xl py-2.5 pl-10 pr-4 focus:ring-2 focus:ring-brand-primary/20 focus:border-brand-primary transition-all outline-none"
              />
            </div>
          </div>
          
          <div>
            <label className="block text-sm font-bold text-slate-700 mb-1.5 uppercase tracking-wide">Facility Code</label>
            <div className="relative">
              <Hash className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-slate-400" />
              <input
                type="text"
                required
                value={code}
                onChange={(e) => setCode(e.target.value)}
                placeholder="e.g. CH-01"
                className="w-full bg-slate-50 border border-slate-200 text-slate-900 rounded-xl py-2.5 pl-10 pr-4 focus:ring-2 focus:ring-brand-primary/20 focus:border-brand-primary transition-all outline-none uppercase"
              />
            </div>
          </div>

          <div>
            <label className="block text-sm font-bold text-slate-700 mb-1.5 uppercase tracking-wide">Physical Address</label>
            <div className="relative">
              <MapPin className="absolute left-3 top-3 w-5 h-5 text-slate-400" />
              <textarea
                value={address}
                onChange={(e) => setAddress(e.target.value)}
                placeholder="e.g. 123 Industrial Parkway"
                rows={3}
                className="w-full bg-slate-50 border border-slate-200 text-slate-900 rounded-xl py-2.5 pl-10 pr-4 focus:ring-2 focus:ring-brand-primary/20 focus:border-brand-primary transition-all outline-none resize-none"
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
            disabled={isPending || !name || !code}
            className="flex-1 btn-primary flex justify-center items-center gap-2"
          >
            {isPending ? (
              <Loader2 className="w-5 h-5 animate-spin" />
            ) : initialData ? (
              'Update Warehouse'
            ) : (
              'Create Warehouse'
            )}
          </button>
        </div>
      </form>
    </Modal>
  );
};
