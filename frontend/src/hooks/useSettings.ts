import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import api from '../services/api';
import { downloadAuthenticatedFile } from '../lib/download';
import { useToast } from '../context/ToastContext';

export interface OrganizationSettings {
  id: number;
  name: string;
  code: string;
  description?: string;
  logo_url?: string;
  preferences?: Record<string, unknown>;
  is_active: boolean;
}

type SettingsResponse = {
  success?: boolean;
  organization: OrganizationSettings;
  message?: string;
};

export const useOrganizationSettings = () => {
  return useQuery({
    queryKey: ['settings', 'organization'],
    queryFn: async () => {
      const response = await api.get<SettingsResponse>('/settings/organization');
      const body = response.data;
      if (body.organization) {
        return body.organization;
      }
      throw new Error('Invalid settings response');
    },
    retry: 1,
  });
};

export const useUpdateOrganizationSettings = () => {
  const queryClient = useQueryClient();
  const { addToast } = useToast();

  return useMutation({
    mutationFn: async (data: Partial<OrganizationSettings>) => {
      const response = await api.put<SettingsResponse>(
        '/settings/organization',
        data,
      );
      return response.data;
    },
    onSuccess: (data) => {
      addToast(
        'success',
        'Settings Saved',
        data.message || 'Organization settings updated.',
      );
      queryClient.invalidateQueries({ queryKey: ['settings', 'organization'] });
      queryClient.invalidateQueries({ queryKey: ['dashboard-summary'] });
    },
    onError: (error: any) => {
      addToast(
        'error',
        'Update Failed',
        error.response?.data?.message ||
          error.forbiddenMessage ||
          'Could not save settings',
      );
    },
  });
};

export const useUploadOrganizationLogo = () => {
  const queryClient = useQueryClient();
  const { addToast } = useToast();

  return useMutation({
    mutationFn: async (file: File) => {
      if (file.size > 2 * 1024 * 1024) {
        throw new Error('Logo must be 2MB or smaller');
      }
      const formData = new FormData();
      formData.append('logo', file);
      const response = await api.post<{ message: string; logo_url: string }>(
        '/settings/organization/logo',
        formData,
        {
          headers: { 'Content-Type': 'multipart/form-data' },
        },
      );
      return response.data;
    },
    onSuccess: (data) => {
      addToast('success', 'Logo Uploaded', data.message);
      queryClient.invalidateQueries({ queryKey: ['settings', 'organization'] });
    },
    onError: (error: any) => {
      addToast(
        'error',
        'Upload Failed',
        error.response?.data?.message ||
          error.message ||
          'Could not upload logo',
      );
    },
  });
};

export const useExportData = () => {
  const { addToast } = useToast();

  return useMutation({
    mutationFn: async () => {
      await downloadAuthenticatedFile(
        '/settings/organization/export',
        {},
        `institutional_export_${new Date().toISOString().split('T')[0]}.csv`,
        'POST',
      );
    },
    onSuccess: () => {
      addToast('success', 'Export Complete', 'Your data export has been downloaded.');
    },
    onError: (error: any) => {
      addToast(
        'error',
        'Export Failed',
        error.response?.data?.message || 'Could not generate data export.',
      );
    },
  });
};

export const usePurgeData = () => {
  const { addToast } = useToast();

  return useMutation({
    mutationFn: async () => {
      const response = await api.delete<{
        message: string;
        records_deleted: number;
      }>('/settings/organization/purge');
      return response.data;
    },
    onSuccess: (data) => {
      addToast('success', 'Data Purged', data.message);
    },
    onError: (error: any) => {
      addToast(
        'error',
        'Purge Failed',
        error.response?.data?.message || 'Could not purge data.',
      );
    },
  });
};
