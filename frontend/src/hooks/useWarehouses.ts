import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import api from '../services/api';
import type { WarehouseUtilization } from '../types';

export const useWarehouses = () => {
  return useQuery({
    queryKey: ['warehouses'],
    queryFn: async () => {
      const response = await api.get<WarehouseUtilization[]>('/analytics/dashboard/warehouses');
      return response.data;
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
    },
  });
};
