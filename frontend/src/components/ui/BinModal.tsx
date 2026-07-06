import React, { useState, useEffect } from 'react';
import { Modal } from './Modal';
import { Box, Hash, Layers, Info, Edit2, Trash2 } from 'lucide-react';
import { useCreateBin, useWarehouseBins, useUpdateBin, useDeleteBin } from '../../hooks/useWarehouses';
import { useToast } from '../../context/ToastContext';

interface BinModalProps {
  isOpen: boolean;
  onClose: () => void;
  warehouseId: number;
  warehouseName: string;
}

export const BinModal: React.FC<BinModalProps> = ({ isOpen, onClose, warehouseId, warehouseName }) => {
  const { addToast } = useToast();
  const createBin = useCreateBin();
  const updateBin = useUpdateBin();
  const deleteBin = useDeleteBin();
  const { data: bins = [], isLoading: binsLoading } = useWarehouseBins(warehouseId);
  const [formData, setFormData] = useState({
    code: '',
    description: '',
  });
  const [editingBin, setEditingBin] = useState<any | null>(null);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!formData.code) return;

    try {
      if (editingBin) {
        await updateBin.mutateAsync({ warehouseId, binId: editingBin.id, data: formData });
        addToast('success', 'Bin Updated', `Bin ${formData.code} updated.`);
      } else {
        await createBin.mutateAsync({ warehouseId, data: formData });
        addToast('success', 'Bin Created', `New storage bin ${formData.code} added to ${warehouseName}.`);
      }
      onClose();
      setFormData({ code: '', description: '' });
      setEditingBin(null);
    } catch (err) {
      addToast('error', 'Operation Failed', 'Could not create bin. Verify authorization and network.');
    }
  };

  const handleEdit = (bin: any) => {
    setEditingBin(bin);
    setFormData({ code: bin.code || '', description: bin.description || '' });
  };

  const handleDelete = async (bin: any) => {
    if (!window.confirm(`Delete bin ${bin.code}? This action cannot be undone.`)) return;
    try {
      await deleteBin.mutateAsync({ warehouseId, binId: bin.id });
      addToast('success', 'Deleted', `Bin ${bin.code} removed.`);
      // Refresh handled by hooks' invalidation
    } catch (err) {
      addToast('error', 'Delete Failed', 'Could not delete bin.');
    }
  };

  useEffect(() => {
    if (!isOpen) {
      setEditingBin(null);
      setFormData({ code: '', description: '' });
    }
  }, [isOpen]);

  return (
    <Modal
      isOpen={isOpen}
      onClose={onClose}
      title={editingBin ? `Edit Bin ${editingBin.code}` : `Manage Bins — ${warehouseName}`}
      size="md"
      footer={
        <>
          <button onClick={onClose} className="btn-secondary">Cancel</button>
          {editingBin ? (
            <button
              onClick={async () => {
                // attempt to save via handleSubmit
                await handleSubmit(new Event('submit') as any);
              }}
              disabled={updateBin.isPending || !formData.code}
              className="btn-primary"
            >
              {updateBin.isPending ? 'Updating...' : 'Update Bin'}
            </button>
          ) : (
            <button
              onClick={handleSubmit}
              disabled={createBin.isPending || !formData.code}
              className="btn-primary"
            >
              {createBin.isPending ? 'Allocating...' : 'Create Bin'}
            </button>
          )}
          {editingBin && (
            <button
              onClick={() => handleDelete(editingBin)}
              className="btn-danger ml-2"
            >
              <Trash2 className="w-4 h-4 inline-block mr-2" /> Delete
            </button>
          )}
        </>
      }
    >
      <div className="space-y-4">
        <div className="bg-amber-50 border border-amber-200 p-4 rounded-xl flex gap-3">
          <Info className="w-5 h-5 text-amber-600 shrink-0" />
          <p className="text-[11px] text-amber-800 leading-normal font-medium">
            New bins are automatically assigned to the <span className="font-bold whitespace-nowrap">Default Topology</span> (Zone 1, Rack 1, Shelf 1). You can adjust spatial routing in advanced settings.
          </p>
        </div>

        <div className="grid gap-4">
          <div>
            <h4 className="text-sm font-bold text-slate-700 mb-2">Existing Bins</h4>
            <div className="space-y-2">
              {binsLoading ? (
                <p className="text-sm text-slate-500">Loading bins...</p>
              ) : bins.length === 0 ? (
                <p className="text-sm text-slate-500">No bins yet. Create one using the form below.</p>
              ) : (
                bins.map((b: any) => (
                  <div key={b.id} className="flex items-center justify-between p-3 bg-slate-50 rounded-lg border">
                    <div>
                      <div className="font-mono font-bold">{b.code}</div>
                      <div className="text-xs text-slate-500">{b.description || '—'}</div>
                    </div>
                    <div className="flex gap-2">
                      <button onClick={() => handleEdit(b)} className="p-2 text-slate-500 hover:text-brand-primary rounded-md">
                        <Edit2 className="w-4 h-4" />
                      </button>
                      <button onClick={() => handleDelete(b)} className="p-2 text-rose-600 hover:bg-rose-50 rounded-md">
                        <Trash2 className="w-4 h-4" />
                      </button>
                    </div>
                  </div>
                ))
              )}
            </div>
          </div>

          <form onSubmit={handleSubmit} className="space-y-6">
            <div className="space-y-2">
              <label className="text-xs font-bold text-slate-500 uppercase tracking-wider flex items-center gap-2">
                <Hash className="w-3 h-3" /> Bin Code / Label
              </label>
              <input
                type="text"
                required
                className="input-field font-mono"
                placeholder="e.g. WH1-A1-042"
                value={formData.code}
                onChange={e => setFormData({ ...formData, code: e.target.value.toUpperCase() })}
              />
            </div>

            <div className="space-y-2">
              <label className="text-xs font-bold text-slate-500 uppercase tracking-wider flex items-center gap-2">
                <Layers className="w-3 h-3" /> Description
              </label>
              <textarea
                className="input-field h-24 resize-none"
                placeholder="Optional notes or location cues..."
                value={formData.description}
                onChange={e => setFormData({ ...formData, description: e.target.value })}
              />
            </div>
          </form>
        </div>
      </div>
    </Modal>
  );
};
