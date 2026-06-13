import { useQuery } from '@tanstack/react-query';
import api from '../services/api';
import type {
  AssetsReportData,
  DashboardReportData,
  InventoryReportData,
  ReportEnvelope,
  TrackingReportData,
} from '../types/reports';

const fetchReport = async <T>(path: string, days: number): Promise<T> => {
  const { data } = await api.get<ReportEnvelope<T>>(path, {
    params: { days },
  });
  if (!data.success) {
    throw new Error(data.message || 'Report request failed');
  }
  return data.data;
};

export const useAssetsReport = (days = 30, enabled = true) =>
  useQuery({
    queryKey: ['reports', 'assets', days],
    queryFn: () => fetchReport<AssetsReportData>('/reports/assets', days),
    enabled,
    staleTime: 60_000,
    refetchInterval: 60_000,
  });

export const useInventoryReport = (days = 30, enabled = true) =>
  useQuery({
    queryKey: ['reports', 'inventory', days],
    queryFn: () => fetchReport<InventoryReportData>('/reports/inventory', days),
    enabled,
    staleTime: 60_000,
    refetchInterval: 60_000,
  });

export const useTrackingReport = (days = 30, enabled = true) =>
  useQuery({
    queryKey: ['reports', 'tracking', days],
    queryFn: () => fetchReport<TrackingReportData>('/reports/tracking', days),
    enabled,
    staleTime: 60_000,
    refetchInterval: 60_000,
  });

export const useDashboardReport = (days = 30) =>
  useQuery({
    queryKey: ['reports', 'dashboard', days],
    queryFn: () => fetchReport<DashboardReportData>('/reports/dashboard', days),
    staleTime: 60_000,
    refetchInterval: 30_000,
  });
