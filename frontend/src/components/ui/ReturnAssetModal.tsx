import React, { useState, useEffect } from 'react';
import { CornerDownLeft } from 'lucide-react';
import { Modal } from './Modal';
import { useReturnAsset } from '../../hooks/useAssets';
import type { ReturnAssetPayload } from '../../hooks/useAssets';
import { useToast } from '../../context/ToastContext';
import type { Asset } from '../../types';

interface ReturnAssetModalProps {
  isOpen: boolean;
  onClose: () => void;
  asset: Asset | null;
}

const CONDITIONS: { value: ReturnAssetPayload['return_condition']; label: string; description: string }[] = [
  { value: 'good',    label: 'Good',    description: 'Asset is in working condition' },
  { value: 'damaged', label: 'Damaged', description: 'Asset needs repair' },
  { value: 'lost',    label: 'Lost',    description: 'Asset cannot be located' },
];

const SUCCESS_MESSAGES: Record<ReturnAssetPayload['return_condition'], string> = {
  good:    'returned — marked as available.',
  damaged: 'returned damaged — flagged for repair.',
  lost:    'reported as lost.',
};

export const ReturnAssetModal: React.FC<ReturnAssetModalProps> = ({ isOpen, onClose, asset }) => {
  const { addToast } = useToast();
  const returnAsset = useReturnAsset();

  const today = new Date().toISOString().split('T')[0];

  const [formData, setFormData] = useState<{
    return_condition: ReturnAssetPayload['return_condition'];
    actual_return_date: string;
    notes: string;
  }>({ return_condition: 'good', actual_return_date: today, notes: '' });

  useEffect(() => {
    if (isOpen) {
      setFormData({ return_condition: 'good', actual_return_date: today, notes: '' });
    }
  }, [isOpen]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!asset) return;

    try {
      await returnAsset.mutateAsync({
        assetId: asset.id,
        data: {
          return_condition: formData.return_condition,
          actual_return_date: formData.actual_return_date,
          notes: formData.notes || undefined,
        },
      });
      addToast('success', 'Asset Returned', `${asset.name} ${SUCCESS_MESSAGES[formData.return_condition]}`);
      onClose();
    } catch (err: any) {
      const msg = err.response?.data?.message || 'Failed to process return. Please try again.';
      addToast('error', 'Return Failed', msg);
    }
  };

  return (
    <Modal
      isOpen={isOpen}
      onClose={onClose}
      title="Record Asset Return"
      size="sm"
    >
      {asset && (
        <div className="space-y-5">
          <div className="flex items-center gap-3 p-3 bg-amber-50 rounded-xl border border-amber-100">
            <div className="w-8 h-8 rounded-lg bg-amber-100 flex items-center justify-center flex-shrink-0">
              <CornerDownLeft className="w-4 h-4 text-amber-600" />
            </div>
            <div className="min-w-0">
              <p className="text-[11px] font-bold text-amber-500 uppercase tracking-widest">Returning</p>
              <p className="text-sm font-bold text-amber-800 truncate">{asset.name}</p>
              <p className="text-[11px] text-amber-400">{asset.asset_code}</p>
            </div>
            {asset.assigned_to && (
              <div className="ml-auto text-right flex-shrink-0">
                <p className="text-[10px] text-amber-400 uppercase tracking-wider">Assigned to</p>
                <p className="text-[12px] font-semibold text-amber-700 truncate max-w-[120px]">{asset.assigned_to}</p>
              </div>
            )}
          </div>

          <form onSubmit={handleSubmit} className="space-y-4">
            <div>
              <label className="block text-xs font-bold text-slate-500 uppercase tracking-widest mb-2">
                Return Condition <span className="text-rose-500">*</span>
              </label>
              <div className="space-y-2">
                {CONDITIONS.map(({ value, label, description }) => (
                  <label
                    key={value}
                    className={`flex items-center gap-3 p-3 rounded-xl border cursor-pointer transition-all ${
                      formData.return_condition === value
                        ? 'border-amber-300 bg-amber-50'
                        : 'border-slate-200 bg-white hover:border-slate-300'
                    }`}
                  >
                    <input
                      type="radio"
                      name="return_condition"
                      value={value}
                      checked={formData.return_condition === value}
                      onChange={() => setFormData(prev => ({ ...prev, return_condition: value }))}
                      className="accent-amber-600"
                    />
                    <div>
                      <p className="text-sm font-semibold text-slate-700">{label}</p>
                      <p className="text-[11px] text-slate-400">{description}</p>
                    </div>
                  </label>
                ))}
              </div>
            </div>

            <div>
              <label className="block text-xs font-bold text-slate-500 uppercase tracking-widest mb-1.5">
                Return Date <span className="text-rose-500">*</span>
              </label>
              <input
                type="date"
                required
                max={today}
                value={formData.actual_return_date}
                onChange={e => setFormData(prev => ({ ...prev, actual_return_date: e.target.value }))}
                className="w-full border border-slate-200 rounded-xl py-2.5 px-3 text-sm focus:ring-4 focus:ring-amber-500/10 focus:border-amber-300 transition-all outline-none shadow-sm"
              />
            </div>

            <div>
              <label className="block text-xs font-bold text-slate-500 uppercase tracking-widest mb-1.5">
                Notes
                <span className="text-slate-400 font-normal normal-case tracking-normal ml-1">(optional)</span>
              </label>
              <textarea
                rows={2}
                maxLength={1000}
                placeholder="Describe damage, circumstances, etc."
                value={formData.notes}
                onChange={e => setFormData(prev => ({ ...prev, notes: e.target.value }))}
                className="w-full border border-slate-200 rounded-xl py-2.5 px-3 text-sm focus:ring-4 focus:ring-amber-500/10 focus:border-amber-300 transition-all outline-none shadow-sm resize-none"
              />
            </div>

            <div className="flex gap-3 pt-2">
              <button
                type="button"
                onClick={onClose}
                className="btn-secondary flex-1"
              >
                Cancel
              </button>
              <button
                type="submit"
                disabled={returnAsset.isPending}
                className="flex-1 flex items-center justify-center gap-2 px-4 py-2.5 rounded-xl text-sm font-bold bg-amber-600 hover:bg-amber-700 text-white transition-colors disabled:opacity-50"
              >
                <CornerDownLeft className="w-4 h-4" />
                {returnAsset.isPending ? 'Processing...' : 'Confirm Return'}
              </button>
            </div>
          </form>
        </div>
      )}
    </Modal>
  );
};
