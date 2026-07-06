import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import api from '../services/api';
import type { InventoryItem, InventoryBatch, StockUpdate } from '../types';

export const useInventory = (params: any = {}) => {
  return useQuery({
    queryKey: ['inventory', params],
    queryFn: async () => {
      const response = await api.get<{ inventory: InventoryItem[], pagination: any }>('/inventory', { params });
      return response.data;
    },
  });
};

export const useUpdateStock = () => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async ({ id, quantity, type, reference, notes, warehouse_id, destination_warehouse_id }: {
      id: number;
      quantity: number;
      type: 'IN' | 'OUT';
      reference: string;
      notes?: string;
      warehouse_id?: number;
      destination_warehouse_id?: number;
    }) => {
      const response = await api.post(`/inventory/${id}/stock`, {
        quantity,
        type,
        reference,
        notes,
        warehouse_id,
        destination_warehouse_id,
      });
      return response.data;
    },
    onSuccess: (_, variables) => {
      queryClient.invalidateQueries({ queryKey: ['inventory'] });
      queryClient.invalidateQueries({ queryKey: ['dashboard-summary'] });
      queryClient.invalidateQueries({ queryKey: ['item-warehouse-stock'] });
      queryClient.invalidateQueries({ queryKey: ['inventory', { search: undefined, page: 1 }] });
      queryClient.invalidateQueries({ queryKey: ['inventory', { search: undefined }] });
      queryClient.invalidateQueries({ queryKey: ['inventory', variables.id] });
    },
  });
};

export interface WarehouseStockLevel {
  warehouse_id: number;
  warehouse_name: string;
  warehouse_code: string;
  quantity_on_hand: number;
  quantity_reserved: number;
  quantity_available: number;
}

/** Returns per-warehouse stock breakdown for a single inventory item. */
export const useItemWarehouseStock = (itemId: number | undefined) => {
  return useQuery({
    queryKey: ['item-warehouse-stock', itemId],
    queryFn: async () => {
      const response = await api.get<WarehouseStockLevel[]>(`/inventory/${itemId}/warehouse-stock`);
      return response.data;
    },
    enabled: !!itemId,
    staleTime: 10_000, // 10 s
  });
};

export const useCreateInventoryItem = () => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (data: Partial<InventoryItem>) => {
      const response = await api.post('/inventory', data);
      return response.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['inventory'] });
    },
  });
};

export const useUpdateInventoryItem = () => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async ({ id, ...data }: Partial<InventoryItem> & { id: number }) => {
      const response = await api.put(`/inventory/${id}`, data);
      return response.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['inventory'] });
      queryClient.invalidateQueries({ queryKey: ['dashboard-summary'] });
    },
  });
};

export const useBulkImportInventory = () => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (items: Record<string, unknown>[]) => {
      const response = await api.post('/inventory/bulk', { items });
      return response.data as { succeeded: number; failed: number; results: { row: number; status: string; item_id?: number; sku?: string; errors?: Record<string, unknown> }[] };
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['inventory'] });
      queryClient.invalidateQueries({ queryKey: ['dashboard-summary'] });
    },
  });
};

export const useBatchUpdateStock = () => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (rows: any[]) => {
      const response = await api.post('/inventory/batch', { rows });
      return response.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['inventory'] });
      queryClient.invalidateQueries({ queryKey: ['dashboard-summary'] });
    },
  });
};

export const useDeleteInventoryItem = () => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (id: number) => {
      const response = await api.delete(`/inventory/${id}`);
      return response.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['inventory'] });
      queryClient.invalidateQueries({ queryKey: ['dashboard-summary'] });
    },
  });
};

// ============ BATCH HOOKS ============

export const useBatches = (params: any = {}) => {
  return useQuery({
    queryKey: ['inventory-batches', params],
    queryFn: async () => {
      const response = await api.get<{ batches: InventoryBatch[], pagination: any }>('/inventory/batches', { params });
      return response.data;
    },
  });
};

export const useBatch = (batchId: number | null) => {
  return useQuery({
    queryKey: ['inventory-batch', batchId],
    queryFn: async () => {
      if (!batchId) throw new Error('Batch ID required');
      const response = await api.get<InventoryBatch>(`/inventory/batches/${batchId}`);
      return response.data;
    },
    enabled: !!batchId,
  });
};

export const useCreateBatch = () => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (data: Partial<InventoryBatch>) => {
      const response = await api.post('/inventory/batches', data);
      return response.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['inventory-batches'] });
      queryClient.invalidateQueries({ queryKey: ['inventory'] });
    },
  });
};

export const useUpdateBatch = () => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async ({ id, ...data }: Partial<InventoryBatch> & { id: number }) => {
      const response = await api.put(`/inventory/batches/${id}`, data);
      return response.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['inventory-batches'] });
      queryClient.invalidateQueries({ queryKey: ['inventory'] });
    },
  });
};

export const useDeleteBatch = () => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (id: number) => {
      const response = await api.delete(`/inventory/batches/${id}`);
      return response.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['inventory-batches'] });
      queryClient.invalidateQueries({ queryKey: ['inventory'] });
    },
  });
};

export const useExpiringBatches = (params: any = {}) => {
  return useQuery({
    queryKey: ['expiring-batches', params],
    queryFn: async () => {
      const response = await api.get<{ expiring_batches: InventoryBatch[], count: number }>('/inventory/batches/expiring', { params });
      return response.data;
    },
  });
};

export const useBatchStats = () => {
  return useQuery({
    queryKey: ['batch-stats'],
    queryFn: async () => {
      const response = await api.get('/inventory/batches/stats');
      return response.data;
    },
  });
};
