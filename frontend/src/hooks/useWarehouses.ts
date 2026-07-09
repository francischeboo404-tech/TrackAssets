import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import api from '../services/api';
import type { WarehouseUtilization } from '../types';

export interface OrgWarehouseDetail {
  id: number;
  name: string;
  code: string;
  address?: string | null;
  is_main_warehouse: boolean;
  warehouse_type: 'main' | 'branch';
  hierarchy_level: number;
  stock_units: number;
  asset_count: number;
  asset_value: number;
  department_count: number;
  utilization_percentage: number;
  total_bins: number;
  occupied_bins: number;
}

export interface OrgWarehouseSummary {
  total_warehouses: number;
  total_inventory_value: number;
  total_assets: number;
  total_asset_value: number;
  total_departments: number;
  total_employees: number;
  pending_purchase_requests: number;
  warehouses: OrgWarehouseDetail[];
}

export const useOrgWarehouseSummary = () => {
  return useQuery<OrgWarehouseSummary>({
    queryKey: ['org-warehouse-summary'],
    queryFn: async () => {
      const response = await api.get<OrgWarehouseSummary>('/warehouses/org-summary');
      return response.data;
    },
    staleTime: 30_000,
    refetchInterval: 60_000,
  });
};

export const useWarehouses = () => {
  return useQuery({
    queryKey: ['warehouses'],
    queryFn: async () => {
      const response = await api.get<{ id: number; name: string; code: string; is_active: boolean }[]>('/warehouses');
      // Filter to only active warehouses
      return (response.data || []).filter((w) => w.is_active !== false);
    },
  });
};

export const useWarehouseDetails = (id: number) => {
  return useQuery({
    queryKey: ['warehouse', id],
    queryFn: async () => {
      const response = await api.get(`/warehouses/${id}/bins`);
      return response.data;
    },
    enabled: !!id,
  });
};

export const useWarehouseBins = (warehouseId?: number, itemId?: number) => {
  return useQuery({
    queryKey: ['warehouse-bins', warehouseId, itemId],
    queryFn: async () => {
      if (!warehouseId) {
        return [];
      }
      const response = await api.get(`/warehouses/${warehouseId}/bins`);
      return response.data;
    },
    enabled: !!warehouseId,
  });
};

export const useCreateWarehouse = () => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (data: { name: string; code: string; address?: string }) => {
      const response = await api.post('/warehouses', data);
      return response.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['warehouses'] });
    },
  });
};

export const useUpdateWarehouse = () => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async ({ id, data }: { id: number; data: { name?: string; code?: string; address?: string } }) => {
      const response = await api.put(`/warehouses/${id}`, data);
      return response.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['warehouses'] });
    },
  });
};

export const useDeleteWarehouse = () => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (id: number) => {
      const response = await api.delete(`/warehouses/${id}`);
      return response.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['warehouses'] });
      queryClient.invalidateQueries({ queryKey: ['org-warehouse-summary'] });
    },
  });
};

export const useSetMainWarehouse = () => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (warehouseId: number) => {
      const response = await api.patch(`/warehouses/${warehouseId}/set-main`);
      return response.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['warehouses'] });
      queryClient.invalidateQueries({ queryKey: ['org-warehouse-summary'] });
    },
  });
};

export const useStockTransfer = () => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (transferData: Record<string, unknown>) => {
      const response = await api.post('/transfers/request', {
        item_type: 'inventory',
        ...transferData,
      });
      return response.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['inventory'] });
      queryClient.invalidateQueries({ queryKey: ['warehouses'] });
    },
  });
};

export const useCreateBin = () => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async ({ warehouseId, data }: { warehouseId: number, data: any }) => {
      const response = await api.post(`/warehouses/${warehouseId}/bins`, data);
      return response.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['warehouses'] });
      queryClient.invalidateQueries({ queryKey: ['warehouse'] });
      queryClient.invalidateQueries({ queryKey: ['warehouse-bins'] });
    },
  });
};

export const useUpdateBin = () => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async ({ warehouseId, binId, data }: { warehouseId: number; binId: number; data: any }) => {
      const response = await api.put(`/warehouses/${warehouseId}/bins/${binId}`, data);
      return response.data;
    },
    onSuccess: (_data, variables: any) => {
      queryClient.invalidateQueries({ queryKey: ['warehouses'] });
      queryClient.invalidateQueries({ queryKey: ['warehouse'] });
      queryClient.invalidateQueries({ queryKey: ['warehouse-bins', variables.warehouseId] });
    },
  });
};

export const useDeleteBin = () => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async ({ warehouseId, binId }: { warehouseId: number; binId: number }) => {
      const response = await api.delete(`/warehouses/${warehouseId}/bins/${binId}`);
      return response.data;
    },
    onSuccess: (_data, variables: any) => {
      queryClient.invalidateQueries({ queryKey: ['warehouses'] });
      queryClient.invalidateQueries({ queryKey: ['warehouse'] });
      queryClient.invalidateQueries({ queryKey: ['warehouse-bins', variables.warehouseId] });
    },
  });
};
