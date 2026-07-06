import { useQuery } from '@tanstack/react-query';
import api from '../services/api';
import type {
  AssetsReportData,
  DashboardReportData,
  InventoryReportData,
  ReportEnvelope,
  TrackingReportData,
} from '../types/reports';

const fetchReport = async <T>(path: string, days: number, departmentId?: number): Promise<T> => {
  const params: any = { days };
  if (departmentId) params.department_id = departmentId;
  const { data } = await api.get<ReportEnvelope<T>>(path, { params });
  if (!data.success) {
    throw new Error(data.message || 'Report request failed');
  }
  return data.data;
};

export const useAssetsReport = (days = 30, enabled = true, departmentId?: number) =>
  useQuery({
    queryKey: ['reports', 'assets', days, departmentId],
    queryFn: () => fetchReport<AssetsReportData>('/reports/assets', days, departmentId),
    enabled,
    staleTime: 60_000,
    refetchInterval: 60_000,
  });

export const useInventoryReport = (days = 30, enabled = true, departmentId?: number) =>
  useQuery({
    queryKey: ['reports', 'inventory', days, departmentId],
    queryFn: () => fetchReport<InventoryReportData>('/reports/inventory', days, departmentId),
    enabled,
    staleTime: 60_000,
    refetchInterval: 60_000,
  });

export const useTrackingReport = (days = 30, enabled = true, departmentId?: number) =>
  useQuery({
    queryKey: ['reports', 'tracking', days, departmentId],
    queryFn: () => fetchReport<TrackingReportData>('/reports/tracking', days, departmentId),
    enabled,
    staleTime: 60_000,
    refetchInterval: 60_000,
  });

export const useDashboardReport = (days = 30, departmentId?: number) =>
  useQuery({
    queryKey: ['reports', 'dashboard', days, departmentId],
    queryFn: () => fetchReport<DashboardReportData>('/reports/dashboard', days, departmentId),
    staleTime: 60_000,
    refetchInterval: 30_000,
  });
