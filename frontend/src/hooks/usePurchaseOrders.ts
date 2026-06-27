import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import api from '../services/api';

export const usePurchaseOrders = () => {
  return useQuery({
    queryKey: ['purchase_orders'],
    queryFn: async () => {
      const res = await api.get('/procurement/purchase-orders');
      return res.data.purchase_orders ?? res.data;
    },
  });
};

export const useCreatePurchaseOrder = () => {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (payload: any) => {
      const res = await api.post('/procurement/purchase-orders', payload);
      return res.data;
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['purchase_orders'] });
      qc.invalidateQueries({ queryKey: ['purchase_requests'] });
      qc.invalidateQueries({ queryKey: ['inventory'] });
      qc.invalidateQueries({ queryKey: ['dashboard-summary'] });
    },
  });
};


export const useCanvassPurchaseOrder = () => {
  const qc = useQueryClient();

  return useMutation({
    mutationFn: async ({
      id,
      supplier_name,
      item_name,
      unit_cost,
    }: {
      id: number;
      supplier_name: string;
      item_name: string;
      unit_cost: number;
    }) => {
      const res = await api.post(
        `/procurement/purchase-orders/${id}/canvass`,
        {
          supplier_name,
          item_name,
          unit_cost,
        }
      );

      return res.data;
    },

    onSuccess: () => {
      qc.invalidateQueries({
        queryKey: ["purchase_orders"],
      });
    },
  });
};

export const useApprovePurchaseOrder = () => {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (id: number) => {
      const res = await api.put(`/procurement/purchase-orders/${id}/approve`);
      return res.data;
    },
    onSuccess: () => qc.invalidateQueries({ queryKey: ['purchase_orders'] }),
  });
};

export const useRejectPurchaseOrder = () => {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (id: number) => {
      const res = await api.put(`/procurement/purchase-orders/${id}/reject`);
      return res.data;
    },
    onSuccess: () => qc.invalidateQueries({ queryKey: ['purchase_orders'] }),
  });
};

export default null;
