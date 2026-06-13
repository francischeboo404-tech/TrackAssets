import { Check, X, UserCheck, Wrench, Trash2, RotateCcw } from 'lucide-react';
import { useAssetTransition } from '../../hooks/useAssets';
import { useToast } from '../../context/ToastContext';
import { useAuth } from '../../context/AuthContext';
import { canTransitionAsset } from '../../lib/permissions';
import { cn } from '../../lib/utils';

const ACTION_CONFIG: Record<
  string,
  { label: string; icon: typeof Check; className: string }
> = {
  approved: { label: 'Approve', icon: Check, className: 'bg-indigo-50 text-indigo-700 hover:bg-indigo-100' },
  rejected: { label: 'Reject', icon: X, className: 'bg-rose-50 text-rose-700 hover:bg-rose-100' },
  in_use: { label: 'Mark In Use', icon: UserCheck, className: 'bg-emerald-50 text-emerald-700 hover:bg-emerald-100' },
  maintenance: { label: 'Send to Maintenance', icon: Wrench, className: 'bg-amber-50 text-amber-700 hover:bg-amber-100' },
  disposed: { label: 'Dispose', icon: Trash2, className: 'bg-slate-100 text-slate-700 hover:bg-slate-200' },
  requested: { label: 'Re-request', icon: RotateCcw, className: 'bg-sky-50 text-sky-700 hover:bg-sky-100' },
};

const NEXT_BY_STATUS: Record<string, string[]> = {
  requested: ['approved', 'rejected'],
  rejected: ['requested'],
  approved: ['in_use'],
  in_use: ['maintenance', 'disposed'],
  maintenance: ['in_use', 'disposed'],
};

interface AssetLifecycleActionsProps {
  assetId: number;
  currentStatus: string;
  onSuccess?: () => void;
  compact?: boolean;
}

export const AssetLifecycleActions: React.FC<AssetLifecycleActionsProps> = ({
  assetId,
  currentStatus,
  onSuccess,
  compact = false,
}) => {
  const { user } = useAuth();
  const { addToast } = useToast();
  const transition = useAssetTransition();

  const candidates = NEXT_BY_STATUS[currentStatus] || [];
  const actions = candidates.filter((status) =>
    canTransitionAsset(user?.role, currentStatus, status),
  );

  if (actions.length === 0) return null;

  const handleTransition = async (status: string) => {
    try {
      await transition.mutateAsync({ id: assetId, status });
      addToast('success', 'Status Updated', `Asset is now ${status.replace('_', ' ')}.`);
      onSuccess?.();
    } catch (err: any) {
      const msg =
        err.response?.data?.message ||
        (err.response?.status === 403
          ? 'You do not have permission for this action.'
          : 'Status update failed.');
      addToast('error', 'Update Failed', msg);
    }
  };

  return (
    <div className={cn('flex flex-wrap gap-2', compact && 'gap-1.5')}>
      {actions.map((status) => {
        const cfg = ACTION_CONFIG[status];
        if (!cfg) return null;
        const Icon = cfg.icon;
        return (
          <button
            key={status}
            type="button"
            disabled={transition.isPending}
            onClick={() => handleTransition(status)}
            className={cn(
              'inline-flex items-center gap-1.5 rounded-lg border border-transparent px-3 py-1.5 text-[11px] font-bold transition-colors disabled:opacity-50',
              cfg.className,
              compact && 'px-2 py-1 text-[10px]',
            )}
          >
            <Icon className="w-3.5 h-3.5" />
            {cfg.label}
          </button>
        );
      })}
    </div>
  );
};
