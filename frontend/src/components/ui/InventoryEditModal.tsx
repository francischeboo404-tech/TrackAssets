import React, { useEffect, useState } from 'react';
import { Modal } from './Modal';
import { Package } from 'lucide-react';
import { useUpdateInventoryItem } from '../../hooks/useInventory';
import { useToast } from '../../context/ToastContext';
import type { InventoryItem } from '../../types';

interface InventoryEditModalProps {
  isOpen: boolean;
  onClose: () => void;
  item: InventoryItem | null;
}

export const InventoryEditModal: React.FC<InventoryEditModalProps> = ({
  isOpen,
  onClose,
  item,
}) => {
  const { addToast } = useToast();
  const updateItem = useUpdateInventoryItem();
  const [formData, setFormData] = useState({
    name: '',
    sku: '',
    description: '',
    reorder_level: 10,
    unit_price: 0,
    unit: 'pcs',
  });

  useEffect(() => {
    if (item) {
      setFormData({
        name: item.name,
        sku: item.sku,
        description: item.description || '',
        reorder_level: item.reorder_level,
        unit_price: item.unit_price,
        unit: item.unit || 'pcs',
      });
    }
  }, [item]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!item) return;
    try {
      await updateItem.mutateAsync({ id: item.id, ...formData });
      addToast('success', 'Item Updated', `${formData.name} was saved.`);
      onClose();
    } catch (err: any) {
      const msg =
        err.response?.data?.message ||
        (err.response?.status === 403
          ? 'You do not have permission to edit inventory.'
          : 'Update failed.');
      addToast('error', 'Update Failed', msg);
    }
  };

  return (
    <Modal isOpen={isOpen} onClose={onClose} title="Edit Inventory Item" size="md">
      <form onSubmit={handleSubmit} className="space-y-4 p-1">
        <div className="flex items-center gap-3 mb-2">
          <div className="p-2 bg-brand-50 rounded-lg">
            <Package className="w-5 h-5 text-brand-primary" />
          </div>
          <p className="text-sm text-slate-500">Stock quantity is adjusted via IN/OUT movements only.</p>
        </div>
        <input
          className="input-field w-full"
          value={formData.name}
          onChange={(e) => setFormData({ ...formData, name: e.target.value })}
          placeholder="Item name"
          required
        />
        <input
          className="input-field w-full font-mono text-sm"
          value={formData.sku}
          onChange={(e) => setFormData({ ...formData, sku: e.target.value })}
          placeholder="SKU"
          required
        />
        <textarea
          className="input-field w-full min-h-[80px]"
          value={formData.description}
          onChange={(e) => setFormData({ ...formData, description: e.target.value })}
          placeholder="Description"
        />
        <div className="grid grid-cols-2 gap-3">
          <input
            type="number"
            min={0}
            className="input-field w-full"
            value={formData.reorder_level}
            onChange={(e) =>
              setFormData({ ...formData, reorder_level: Number(e.target.value) })
            }
            placeholder="Reorder level"
          />
          <input
            type="number"
            min={0}
            step="0.01"
            className="input-field w-full"
            value={formData.unit_price}
            onChange={(e) =>
              setFormData({ ...formData, unit_price: Number(e.target.value) })
            }
            placeholder="Unit price"
          />
        </div>
        <div className="flex justify-end gap-2 pt-2">
          <button type="button" className="btn-secondary" onClick={onClose}>
            Cancel
          </button>
          <button type="submit" className="btn-primary" disabled={updateItem.isPending}>
            Save Changes
          </button>
        </div>
      </form>
    </Modal>
  );
};
