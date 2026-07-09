import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import api from '../services/api';

export const usePurchaseRequests = (warehouseId?: number) => {
  return useQuery({
    queryKey: ['purchase_requests', warehouseId],
    queryFn: async () => {
      const params: any = {};
      if (warehouseId) params.warehouse_id = warehouseId;
      const res = await api.get('/procurement/purchase-requests', { params });
      // backend returns { purchase_requests: [...] }
      return res.data.purchase_requests ?? res.data;
    },
  });
};

export const useCreatePurchaseRequest = () => {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (payload: { reason: string; items?: any[] }) => {
      const res = await api.post('/procurement/purchase-requests', payload);
      return res.data;
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['purchase_requests'] });
      qc.invalidateQueries({ queryKey: ['inventory'] });
      qc.invalidateQueries({ queryKey: ['dashboard-summary'] });
    },
  });
};

export const useApprovePurchaseRequest = () => {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (id: number) => {
      const res = await api.put(`/procurement/purchase-requests/${id}/approve`);
      return res.data;
    },
    onSuccess: () => qc.invalidateQueries({ queryKey: ['purchase_requests'] }),
  });
};

export const useRejectPurchaseRequest = () => {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (id: number) => {
      const res = await api.put(`/procurement/purchase-requests/${id}/reject`);
      return res.data;
    },
    onSuccess: () => qc.invalidateQueries({ queryKey: ['purchase_requests'] }),
  });
};

export default null;
