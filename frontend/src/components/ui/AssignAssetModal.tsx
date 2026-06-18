import React, { useState, useEffect } from 'react';
import { UserCheck } from 'lucide-react';
import { Modal } from './Modal';
import { useAssignAsset } from '../../hooks/useAssets';
import { useUsers } from '../../hooks/useUsers';
import { useDepartments } from '../../hooks/useDepartments';
import { useToast } from '../../context/ToastContext';
import type { Asset } from '../../types';

interface AssignAssetModalProps {
  isOpen: boolean;
  onClose: () => void;
  asset: Asset | null;
}

export const AssignAssetModal: React.FC<AssignAssetModalProps> = ({ isOpen, onClose, asset }) => {
  const { addToast } = useToast();
  const assignAsset = useAssignAsset();
  const { data: usersData } = useUsers({ page: 1 });
  const { data: departments } = useDepartments();

  const users = usersData?.users?.filter(u => u.is_active) ?? [];
  const deptList = Array.isArray(departments) ? departments : [];

  const today = new Date().toISOString().split('T')[0];

  const [formData, setFormData] = useState({
    user_id: '',
    department_id: '',
    assignment_date: today,
    return_date: '',
  });

  useEffect(() => {
    if (isOpen && asset) {
      setFormData({
        user_id: '',
        department_id: asset.department_id ? String(asset.department_id) : '',
        assignment_date: today,
        return_date: '',
      });
    }
  }, [isOpen, asset]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!asset) return;
    if (!formData.user_id || !formData.department_id) {
      addToast('error', 'Validation Error', 'Please select an employee and department.');
      return;
    }

    try {
      await assignAsset.mutateAsync({
        assetId: asset.id,
        data: {
          user_id: Number(formData.user_id),
          department_id: Number(formData.department_id),
          assignment_date: formData.assignment_date,
          return_date: formData.return_date || null,
        },
      });

      const assignee = users.find(u => u.id === Number(formData.user_id));
      const name = assignee
        ? `${assignee.first_name || ''} ${assignee.last_name || ''}`.trim() || assignee.username
        : 'employee';

      addToast('success', 'Asset Assigned', `${asset.name} has been assigned to ${name}.`);
      onClose();
    } catch (err: any) {
      const msg = err.response?.data?.message || 'Failed to assign asset. Please try again.';
      addToast('error', 'Assignment Failed', msg);
    }
  };

  return (
    <Modal
      isOpen={isOpen}
      onClose={onClose}
      title="Assign Asset"
      size="sm"
    >
      {asset && (
        <div className="space-y-5">
          <div className="flex items-center gap-3 p-3 bg-indigo-50 rounded-xl border border-indigo-100">
            <div className="w-8 h-8 rounded-lg bg-indigo-100 flex items-center justify-center flex-shrink-0">
              <UserCheck className="w-4 h-4 text-indigo-600" />
            </div>
            <div className="min-w-0">
              <p className="text-[11px] font-bold text-indigo-500 uppercase tracking-widest">Assigning</p>
              <p className="text-sm font-bold text-indigo-800 truncate">{asset.name}</p>
              <p className="text-[11px] text-indigo-400">{asset.asset_code}</p>
            </div>
          </div>

          <form onSubmit={handleSubmit} className="space-y-4">
            <div>
              <label className="block text-xs font-bold text-slate-500 uppercase tracking-widest mb-1.5">
                Employee <span className="text-rose-500">*</span>
              </label>
              <select
                value={formData.user_id}
                onChange={e => setFormData(prev => ({ ...prev, user_id: e.target.value }))}
                required
                className="w-full border border-slate-200 rounded-xl py-2.5 px-3 text-sm focus:ring-4 focus:ring-brand-primary/10 focus:border-brand-primary/20 transition-all outline-none shadow-sm bg-white"
              >
                <option value="">Select employee...</option>
                {users.map(u => (
                  <option key={u.id} value={u.id}>
                    {`${u.first_name || ''} ${u.last_name || ''}`.trim() || u.username} — {u.role}
                  </option>
                ))}
              </select>
            </div>

            <div>
              <label className="block text-xs font-bold text-slate-500 uppercase tracking-widest mb-1.5">
                Department <span className="text-rose-500">*</span>
              </label>
              <select
                value={formData.department_id}
                onChange={e => setFormData(prev => ({ ...prev, department_id: e.target.value }))}
                required
                className="w-full border border-slate-200 rounded-xl py-2.5 px-3 text-sm focus:ring-4 focus:ring-brand-primary/10 focus:border-brand-primary/20 transition-all outline-none shadow-sm bg-white"
              >
                <option value="">Select department...</option>
                {deptList.map(d => (
                  <option key={d.id} value={d.id}>{d.name}</option>
                ))}
              </select>
            </div>

            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className="block text-xs font-bold text-slate-500 uppercase tracking-widest mb-1.5">
                  Assignment Date <span className="text-rose-500">*</span>
                </label>
                <input
                  type="date"
                  value={formData.assignment_date}
                  onChange={e => setFormData(prev => ({ ...prev, assignment_date: e.target.value }))}
                  required
                  className="w-full border border-slate-200 rounded-xl py-2.5 px-3 text-sm focus:ring-4 focus:ring-brand-primary/10 focus:border-brand-primary/20 transition-all outline-none shadow-sm"
                />
              </div>
              <div>
                <label className="block text-xs font-bold text-slate-500 uppercase tracking-widest mb-1.5">
                  Return Date
                  <span className="text-slate-400 font-normal normal-case tracking-normal ml-1">(optional)</span>
                </label>
                <input
                  type="date"
                  value={formData.return_date}
                  min={formData.assignment_date}
                  onChange={e => setFormData(prev => ({ ...prev, return_date: e.target.value }))}
                  className="w-full border border-slate-200 rounded-xl py-2.5 px-3 text-sm focus:ring-4 focus:ring-brand-primary/10 focus:border-brand-primary/20 transition-all outline-none shadow-sm"
                />
              </div>
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
                disabled={assignAsset.isPending}
                className="btn-primary flex-1 flex items-center justify-center gap-2"
              >
                <UserCheck className="w-4 h-4" />
                {assignAsset.isPending ? 'Assigning...' : 'Assign Asset'}
              </button>
            </div>
          </form>
        </div>
      )}
    </Modal>
  );
};
