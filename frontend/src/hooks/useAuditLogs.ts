import { useQuery } from '@tanstack/react-query';
import api from '../services/api';
import type { AuditLog } from '../types';

export interface AuditLogParams {
  page?: number;
  per_page?: number;
  entity_type?: string;
  q?: string;
  user_id?: number;
  date_from?: string;
  date_to?: string;
}

export const useAuditLogs = (params: AuditLogParams = {}) => {
  return useQuery({
    queryKey: ['audit-logs', params],
    queryFn: async () => {
      const response = await api.get<{audit_logs: AuditLog[], pagination: any}>('/audit/logs', { params });
      return response.data.audit_logs;
    },
  });
};

export const useAuditSummary = () => {
  return useQuery({
    queryKey: ['audit-summary'],
    queryFn: async () => {
      const response = await api.get('/audit/summary');
      return response.data as {
        total_actions: number;
        critical_changes: number;
        user_activity: Record<string, number>;
      };
    },
  });
};
