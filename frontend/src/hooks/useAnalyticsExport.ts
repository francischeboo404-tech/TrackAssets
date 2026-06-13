import { useMutation } from '@tanstack/react-query';
import { downloadAuthenticatedFile } from '../lib/download';
import { useToast } from '../context/ToastContext';

export type AnalyticsExportType = 'movement' | 'valuation';

export const useAnalyticsExport = () => {
  const { addToast } = useToast();

  return useMutation({
    mutationFn: async (type: AnalyticsExportType) => {
      const path =
        type === 'movement'
          ? '/analytics/export/movement'
          : '/analytics/export/valuation';
      const stamp = new Date().toISOString().slice(0, 10);
      const name =
        type === 'movement'
          ? `movement_history_${stamp}.csv`
          : `inventory_valuation_${stamp}.csv`;

      await downloadAuthenticatedFile(path, {}, name);
    },
    onSuccess: () => {
      addToast(
        'success',
        'Export Complete',
        'Analytics data has been downloaded as CSV.',
      );
    },
    onError: (error: any) => {
      addToast(
        'error',
        'Export Failed',
        error.response?.data?.message ||
          error.forbiddenMessage ||
          'Could not export analytics data.',
      );
    },
  });
};
