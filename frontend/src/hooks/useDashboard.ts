import { useQuery } from '@tanstack/react-query';
import api from '../services/api';
import type { RestockAlert } from '../types';

export const useDashboardSummary = (warehouseId?: number) => {
  return useQuery({
    queryKey: ['dashboard-summary', warehouseId],
    queryFn: async () => {
      const path = warehouseId 
        ? `/analytics/dashboard/summary?warehouse_id=${warehouseId}`
        : '/analytics/dashboard/summary';
      const response = await api.get(path);
      return response.data as { 
        inventory: { total_items: number; health: Record<string, number> };
        total_valuation: number;
        currency: string;
        assets: { total_assets: number; total_purchase_value: number; total_current_value: number; roi: number; trend: { value: number; isUp: boolean }; status_breakdown: Record<string, number> };
        geospatial: { total_nodes: number; distribution: { name: string; count: number; pct: number }[] };
        compliance: { audit_variance: number; compliance_score: number; trend: { value: number; isUp: boolean }; variance_trend: { value: number; isUp: boolean } };
        recent_activity: { id: number; action: string; entity_type: string; details: any; created_at: string }[];
        movement_stats: Record<string, { IN: number; OUT: number }>;
        insights: any[];
      };
    },
    refetchInterval: 30000,
  });
};

export const useDashboardMovements = (days: number = 7, warehouseId?: number) => {
  return useQuery({
    queryKey: ['dashboard-movements', days, warehouseId],
    queryFn: async () => {
      const params = new URLSearchParams({ days: String(days) });
      if (warehouseId) {
        params.set('warehouse_id', String(warehouseId));
      }
      const response = await api.get(`/analytics/dashboard/movements?${params.toString()}`);
      return response.data as Record<string, { IN: number; OUT: number }>;
    },
  });
};

export const useAlerts = () => {
  return useQuery({
    queryKey: ['active-alerts'],
    queryFn: async () => {
      const response = await api.get<RestockAlert[]>('/restock/alerts');
      return response.data;
    },
  });
};
