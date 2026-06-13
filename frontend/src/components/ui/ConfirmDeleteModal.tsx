import React from 'react';
import { Modal } from './Modal';
import { AlertTriangle } from 'lucide-react';

interface ConfirmDeleteModalProps {
  isOpen: boolean;
  onClose: () => void;
  onConfirm: () => void;
  title: string;
  message: string;
  isLoading?: boolean;
}

export const ConfirmDeleteModal: React.FC<ConfirmDeleteModalProps> = ({
  isOpen,
  onClose,
  onConfirm,
  title,
  message,
  isLoading = false,
}) => (
  <Modal isOpen={isOpen} onClose={onClose} title={title} size="sm">
    <div className="space-y-6 p-1">
      <div className="flex items-start gap-4">
        <div className="p-3 bg-rose-50 rounded-xl">
          <AlertTriangle className="w-6 h-6 text-rose-600" />
        </div>
        <p className="text-sm text-slate-600 leading-relaxed">{message}</p>
      </div>
      <div className="flex justify-end gap-2">
        <button type="button" className="btn-secondary" onClick={onClose} disabled={isLoading}>
          Cancel
        </button>
        <button
          type="button"
          className="btn-primary bg-rose-600 hover:bg-rose-700 border-rose-600"
          onClick={onConfirm}
          disabled={isLoading}
        >
          Delete
        </button>
      </div>
    </div>
  </Modal>
);
