import React, { useState } from 'react';
import { Modal } from './Modal';
import { Box, Hash, Layers, Info } from 'lucide-react';
import { useCreateBin } from '../../hooks/useWarehouses';
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
  const [formData, setFormData] = useState({
    code: '',
    description: '',
  });

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!formData.code) return;

    try {
      await createBin.mutateAsync({ 
        warehouseId, 
        data: formData 
      });
      addToast('success', 'Bin Created', `New storage bin ${formData.code} added to ${warehouseName}.`);
      onClose();
      setFormData({ code: '', description: '' });
    } catch (err) {
      addToast('error', 'Operation Failed', 'Could not create bin. Verify authorization and network.');
    }
  };

  return (
    <Modal 
      isOpen={isOpen} 
      onClose={onClose} 
      title={`Add Bin to ${warehouseName}`} 
      size="md"
      footer={
        <>
          <button onClick={onClose} className="btn-secondary">Cancel</button>
          <button 
            onClick={handleSubmit} 
            disabled={createBin.isPending || !formData.code}
            className="btn-primary"
          >
            {createBin.isPending ? 'Allocating...' : 'Create Bin'}
          </button>
        </>
      }
    >
      <form onSubmit={handleSubmit} className="space-y-6">
        <div className="bg-amber-50 border border-amber-200 p-4 rounded-xl flex gap-3">
          <Info className="w-5 h-5 text-amber-600 shrink-0" />
          <p className="text-[11px] text-amber-800 leading-normal font-medium">
            New bins are automatically assigned to the <span className="font-bold whitespace-nowrap">Default Topology</span> (Zone 1, Rack 1, Shelf 1). You can adjust spatial routing in advanced settings.
          </p>
        </div>

        <div className="space-y-4">
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
              onChange={e => setFormData({...formData, code: e.target.value.toUpperCase()})}
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
              onChange={e => setFormData({...formData, description: e.target.value})}
            />
          </div>
        </div>
      </form>
    </Modal>
  );
};
