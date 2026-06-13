import { useMutation } from '@tanstack/react-query';
import { downloadAuthenticatedFile } from '../lib/download';
import { useToast } from '../context/ToastContext';

export type ReportFormat = 'pdf' | 'excel';

export interface ReportDownloadParams {
  reportId: string;
  format: ReportFormat;
  dateFrom?: string;
  dateTo?: string;
}

const REPORT_PATHS: Record<string, string> = {
  'asset-register': '/reports/asset-register',
  'inventory-register': '/reports/inventory-register',
  'full-export': '/reports/full-export',
  maintenance: '/reports/maintenance',
  disposal: '/reports/disposal',
  'audit-trail': '/reports/audit-trail',
  'department-summary': '/reports/department-summary',
};

const DEFAULT_EXTENSIONS: Record<ReportFormat, string> = {
  pdf: 'pdf',
  excel: 'xlsx',
};

const FALLBACK_NAMES: Record<string, string> = {
  'asset-register': 'asset_register',
  'inventory-register': 'inventory_register',
  'full-export': 'institutional_export',
  maintenance: 'maintenance_report',
  disposal: 'disposal_report',
  'audit-trail': 'audit_trail',
  'department-summary': 'department_summary',
};

function buildParams(
  format: ReportFormat,
  dateFrom?: string,
  dateTo?: string,
): Record<string, string> {
  const params: Record<string, string> = {};
  if (format === 'excel') {
    params.format = 'excel';
  } else if (format === 'pdf') {
    params.format = 'pdf';
  }
  if (dateFrom) {
    params.date_from = new Date(dateFrom).toISOString();
  }
  if (dateTo) {
    params.date_to = new Date(dateTo).toISOString();
  }
  return params;
}

export const useDownloadReport = () => {
  const { addToast } = useToast();

  return useMutation({
    mutationFn: async ({
      reportId,
      format,
      dateFrom,
      dateTo,
    }: ReportDownloadParams) => {
      const path = REPORT_PATHS[reportId];
      if (!path) {
        throw new Error('Unknown report type');
      }

      const params = buildParams(format, dateFrom, dateTo);
      if (reportId === 'full-export') {
        delete params.format;
      }

      const base = FALLBACK_NAMES[reportId] || reportId;
      const ext =
        reportId === 'full-export'
          ? 'xlsx'
          : DEFAULT_EXTENSIONS[format];
      const stamp = new Date().toISOString().slice(0, 10);

      await downloadAuthenticatedFile(
        path,
        params,
        `${base}_${stamp}.${ext}`,
      );
    },
    onSuccess: () => {
      addToast(
        'success',
        'Report Ready',
        'Your institutional report has been downloaded.',
      );
    },
    onError: (error: any) => {
      addToast(
        'error',
        'Download Failed',
        error.response?.data?.message ||
          error.forbiddenMessage ||
          'Could not generate the report. Check your permissions.',
      );
    },
  });
};
