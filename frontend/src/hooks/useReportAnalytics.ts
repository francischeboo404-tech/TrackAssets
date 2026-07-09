import { useQuery } from '@tanstack/react-query';
import api from '../services/api';
import type {
  AssetsReportData,
  DashboardReportData,
  InventoryReportData,
  ReportEnvelope,
  TrackingReportData,
} from '../types/reports';

const fetchReport = async <T>(
  path: string,
  days: number,
  departmentId?: number,
  warehouseId?: number,
): Promise<T> => {
  const params: any = { days };
  if (departmentId) params.department_id = departmentId;
  if (warehouseId) params.warehouse_id = warehouseId;
  const { data } = await api.get<ReportEnvelope<T>>(path, { params });
  if (!data.success) {
    throw new Error(data.message || 'Report request failed');
  }
  return data.data;
};

export const useAssetsReport = (days = 30, enabled = true, departmentId?: number, warehouseId?: number) =>
  useQuery({
    queryKey: ['reports', 'assets', days, departmentId, warehouseId],
    queryFn: () => fetchReport<AssetsReportData>('/reports/assets', days, departmentId, warehouseId),
    enabled,
    staleTime: 60_000,
    refetchInterval: 60_000,
  });

export const useInventoryReport = (days = 30, enabled = true, departmentId?: number, warehouseId?: number) =>
  useQuery({
    queryKey: ['reports', 'inventory', days, departmentId, warehouseId],
    queryFn: () => fetchReport<InventoryReportData>('/reports/inventory', days, departmentId, warehouseId),
    enabled,
    staleTime: 60_000,
    refetchInterval: 60_000,
  });

export const useTrackingReport = (days = 30, enabled = true, departmentId?: number, warehouseId?: number) =>
  useQuery({
    queryKey: ['reports', 'tracking', days, departmentId, warehouseId],
    queryFn: () => fetchReport<TrackingReportData>('/reports/tracking', days, departmentId, warehouseId),
    enabled,
    staleTime: 60_000,
    refetchInterval: 60_000,
  });

export const useDashboardReport = (days = 30, departmentId?: number, warehouseId?: number) =>
  useQuery({
    queryKey: ['reports', 'dashboard', days, departmentId, warehouseId],
    queryFn: () => fetchReport<DashboardReportData>('/reports/dashboard', days, departmentId, warehouseId),
    staleTime: 60_000,
    refetchInterval: 30_000,
  });
