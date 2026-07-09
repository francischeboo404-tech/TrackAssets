import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import api from '../services/api';

export const usePurchaseOrders = (options?: { statuses?: string[]; includeInactive?: boolean }) => {
  return useQuery({
    queryKey: ['purchase_orders', options?.statuses ?? ['approved','partially_received','received'], options?.includeInactive ?? false],
    queryFn: async () => {
      const params = new URLSearchParams();
      const statuses = options?.statuses ?? ['approved', 'partially_received', 'received'];
      statuses.forEach((status) => params.append('status', status));
      if (options?.includeInactive) {
        params.set('include_inactive', 'true');
      }
      const res = await api.get(`/procurement/purchase-orders${params.toString() ? `?${params.toString()}` : ''}`);
      return res.data.purchase_orders ?? res.data;
    },
  });
};

export const usePurchaseOrder = (id?: number | string) => {
  return useQuery({
    queryKey: ['purchaseOrder', id],
    enabled: Boolean(id),
    queryFn: async () => {
      const res = await api.get(`/procurement/purchase-orders/${id}`);
      return res.data;
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
      supplier_id,
      item_id,
      supplier_name,
      item_name,
      unit_cost,
    }: {
      id: number;
      supplier_id?: number | null;
      item_id?: number | null;
      supplier_name?: string;
      item_name?: string;
      unit_cost: number;
    }) => {
      const res = await api.post(
        `/procurement/purchase-orders/${id}/canvass`,
        {
          supplier_id,
          item_id,
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

export const useCloseCanvassQuote = () => {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async ({ po_id, quote_id }: { po_id: number; quote_id: number }) => {
      const res = await api.put(
        `/procurement/purchase-orders/${po_id}/canvass/${quote_id}/close`
      );
      return res.data;
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['purchase_orders'] });
      qc.invalidateQueries({ queryKey: ['purchaseOrder'] });
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
