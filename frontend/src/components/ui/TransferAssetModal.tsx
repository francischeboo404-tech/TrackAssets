import React, { useState, useEffect } from 'react';
import { ArrowRightLeft } from 'lucide-react';
import { Modal } from './Modal';
import { useRequestTransfer } from '../../hooks/useTransfers';
import type { TransferRequestPayload } from '../../hooks/useTransfers';
import { useUsers } from '../../hooks/useUsers';
import { useDepartments } from '../../hooks/useDepartments';
import { useWarehouses } from '../../hooks/useWarehouses';
import { useToast } from '../../context/ToastContext';
import type { Asset } from '../../types';

type TransferType = TransferRequestPayload['transfer_type'];

const TRANSFER_TYPES: {
  value: TransferType;
  label: string;
  description: string;
  requiresAssigned?: boolean;
}[] = [
  {
    value: 'employee_to_employee',
    label: 'Employee to Employee',
    description: 'Reassign to a different employee',
    requiresAssigned: true,
  },
  {
    value: 'department_to_department',
    label: 'Department to Department',
    description: 'Move to a different department',
  },
  {
    value: 'warehouse_to_warehouse',
    label: 'Warehouse to Warehouse',
    description: 'Relocate between warehouse branches',
  },
];

interface TransferAssetModalProps {
  isOpen: boolean;
  onClose: () => void;
  asset: Asset | null;
}

export const TransferAssetModal: React.FC<TransferAssetModalProps> = ({ isOpen, onClose, asset }) => {
  const { addToast } = useToast();
  const requestTransfer = useRequestTransfer();
  const { data: usersData } = useUsers({ page: 1 });
  const { data: departments } = useDepartments();
  const { data: warehousesData } = useWarehouses();

  const users = (usersData as any)?.users?.filter((u: any) => u.is_active) ?? [];
  const deptList = Array.isArray(departments) ? departments : [];
  const warehouseList = Array.isArray(warehousesData) ? warehousesData : [];

  const isAssigned = asset?.status === 'assigned';

  const [transferType, setTransferType] = useState<TransferType>('department_to_department');
  const [toUserId, setToUserId] = useState('');
  const [newDepartmentId, setNewDepartmentId] = useState('');
  const [toWarehouseId, setToWarehouseId] = useState('');
  const [comment, setComment] = useState('');

  useEffect(() => {
    if (isOpen && asset) {
      setTransferType(asset.status === 'assigned' ? 'employee_to_employee' : 'department_to_department');
      setToUserId('');
      setNewDepartmentId('');
      setToWarehouseId('');
      setComment('');
    }
  }, [isOpen, asset]);

  const handleTypeChange = (value: TransferType) => {
    setTransferType(value);
    setToUserId('');
    setNewDepartmentId('');
    setToWarehouseId('');
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!asset) return;

    if (!comment.trim()) {
      addToast('error', 'Validation Error', 'Please provide a reason for the transfer.');
      return;
    }

    const payload: TransferRequestPayload = {
      transfer_type: transferType,
      asset_id: asset.id,
      comment: comment.trim(),
    };

    if (transferType === 'employee_to_employee') {
      if (!toUserId) {
        addToast('error', 'Validation Error', 'Please select a destination employee.');
        return;
      }
      payload.to_user_id = Number(toUserId);
    } else if (transferType === 'department_to_department') {
      if (!newDepartmentId) {
        addToast('error', 'Validation Error', 'Please select a destination department.');
        return;
      }
      payload.new_department_id = Number(newDepartmentId);
    } else {
      if (!toWarehouseId) {
        addToast('error', 'Validation Error', 'Please select a destination warehouse.');
        return;
      }
      payload.to_warehouse_id = Number(toWarehouseId);
    }

    try {
      await requestTransfer.mutateAsync(payload);
      const typeLabel = TRANSFER_TYPES.find(t => t.value === transferType)?.label ?? 'Transfer';
      addToast(
        'success',
        'Transfer Requested',
        `${asset.name}: ${typeLabel} transfer submitted for approval.`
      );
      onClose();
    } catch (err: any) {
      const msg = err.response?.data?.message || 'Failed to submit transfer request. Please try again.';
      addToast('error', 'Transfer Failed', msg);
    }
  };

  // For employee transfers: exclude the current assignee from the list
  const eligibleUsers = users.filter((u: any) => u.id !== asset?.assigned_to_user_id);

  return (
    <Modal isOpen={isOpen} onClose={onClose} title="Transfer Asset" size="sm">
      {asset && (
        <div className="space-y-5">
          {/* Asset header */}
          <div className="flex items-center gap-3 p-3 bg-teal-50 rounded-xl border border-teal-100">
            <div className="w-8 h-8 rounded-lg bg-teal-100 flex items-center justify-center flex-shrink-0">
              <ArrowRightLeft className="w-4 h-4 text-teal-600" />
            </div>
            <div className="min-w-0">
              <p className="text-[11px] font-bold text-teal-500 uppercase tracking-widest">Transferring</p>
              <p className="text-sm font-bold text-teal-800 truncate">{asset.name}</p>
              <p className="text-[11px] text-teal-400">{asset.asset_code}</p>
            </div>
            {asset.assigned_to && (
              <div className="ml-auto text-right flex-shrink-0">
                <p className="text-[10px] text-teal-400 uppercase tracking-wider">Currently with</p>
                <p className="text-[12px] font-semibold text-teal-700 truncate max-w-[120px]">{asset.assigned_to}</p>
              </div>
            )}
          </div>

          <form onSubmit={handleSubmit} className="space-y-4">
            {/* Transfer type radio */}
            <div>
              <label className="block text-xs font-bold text-slate-500 uppercase tracking-widest mb-2">
                Transfer Type <span className="text-rose-500">*</span>
              </label>
              <div className="space-y-2">
                {TRANSFER_TYPES.map(({ value, label, description, requiresAssigned }) => {
                  const disabled = !!(requiresAssigned && !isAssigned);
                  return (
                    <label
                      key={value}
                      className={`flex items-center gap-3 p-3 rounded-xl border transition-all ${
                        disabled
                          ? 'opacity-40 cursor-not-allowed border-slate-200 bg-slate-50'
                          : transferType === value
                          ? 'border-teal-300 bg-teal-50 cursor-pointer'
                          : 'border-slate-200 bg-white hover:border-slate-300 cursor-pointer'
                      }`}
                    >
                      <input
                        type="radio"
                        name="transfer_type"
                        value={value}
                        checked={transferType === value}
                        disabled={disabled}
                        onChange={() => handleTypeChange(value)}
                        className="accent-teal-600"
                      />
                      <div>
                        <p className="text-sm font-semibold text-slate-700">{label}</p>
                        <p className="text-[11px] text-slate-400">
                          {disabled ? 'Asset must be assigned to use this type' : description}
                        </p>
                      </div>
                    </label>
                  );
                })}
              </div>
            </div>

            {/* Dynamic destination field */}
            {transferType === 'employee_to_employee' && (
              <div>
                <label className="block text-xs font-bold text-slate-500 uppercase tracking-widest mb-1.5">
                  Transfer To (Employee) <span className="text-rose-500">*</span>
                </label>
                <select
                  value={toUserId}
                  onChange={e => setToUserId(e.target.value)}
                  required
                  className="w-full border border-slate-200 rounded-xl py-2.5 px-3 text-sm focus:ring-4 focus:ring-teal-500/10 focus:border-teal-300 transition-all outline-none shadow-sm bg-white"
                >
                  <option value="">Select employee...</option>
                  {eligibleUsers.map((u: any) => (
                    <option key={u.id} value={u.id}>
                      {`${u.first_name || ''} ${u.last_name || ''}`.trim() || u.username} — {u.role}
                    </option>
                  ))}
                </select>
              </div>
            )}

            {transferType === 'department_to_department' && (
              <div>
                <label className="block text-xs font-bold text-slate-500 uppercase tracking-widest mb-1.5">
                  Transfer To (Department) <span className="text-rose-500">*</span>
                </label>
                <select
                  value={newDepartmentId}
                  onChange={e => setNewDepartmentId(e.target.value)}
                  required
                  className="w-full border border-slate-200 rounded-xl py-2.5 px-3 text-sm focus:ring-4 focus:ring-teal-500/10 focus:border-teal-300 transition-all outline-none shadow-sm bg-white"
                >
                  <option value="">Select department...</option>
                  {deptList
                    .filter((d: any) => d.id !== asset.department_id)
                    .map((d: any) => (
                      <option key={d.id} value={d.id}>{d.name}</option>
                    ))}
                </select>
              </div>
            )}

            {transferType === 'warehouse_to_warehouse' && (
              <div>
                <label className="block text-xs font-bold text-slate-500 uppercase tracking-widest mb-1.5">
                  Transfer To (Warehouse) <span className="text-rose-500">*</span>
                </label>
                <select
                  value={toWarehouseId}
                  onChange={e => setToWarehouseId(e.target.value)}
                  required
                  className="w-full border border-slate-200 rounded-xl py-2.5 px-3 text-sm focus:ring-4 focus:ring-teal-500/10 focus:border-teal-300 transition-all outline-none shadow-sm bg-white"
                >
                  <option value="">Select warehouse...</option>
                  {warehouseList
                    .filter((w: any) => w.warehouse_id !== asset.warehouse_id)
                    .map((w: any) => (
                      <option key={w.warehouse_id} value={w.warehouse_id}>{w.warehouse_name}</option>
                    ))}
                </select>
              </div>
            )}

            {/* Reason */}
            <div>
              <label className="block text-xs font-bold text-slate-500 uppercase tracking-widest mb-1.5">
                Reason <span className="text-rose-500">*</span>
              </label>
              <textarea
                rows={2}
                maxLength={1000}
                required
                placeholder="Explain the reason for this transfer..."
                value={comment}
                onChange={e => setComment(e.target.value)}
                className="w-full border border-slate-200 rounded-xl py-2.5 px-3 text-sm focus:ring-4 focus:ring-teal-500/10 focus:border-teal-300 transition-all outline-none shadow-sm resize-none"
              />
            </div>

            <div className="flex gap-3 pt-2">
              <button type="button" onClick={onClose} className="btn-secondary flex-1">
                Cancel
              </button>
              <button
                type="submit"
                disabled={requestTransfer.isPending}
                className="flex-1 flex items-center justify-center gap-2 px-4 py-2.5 rounded-xl text-sm font-bold bg-teal-600 hover:bg-teal-700 text-white transition-colors disabled:opacity-50"
              >
                <ArrowRightLeft className="w-4 h-4" />
                {requestTransfer.isPending ? 'Submitting...' : 'Submit Transfer'}
              </button>
            </div>
          </form>
        </div>
      )}
    </Modal>
  );
};
