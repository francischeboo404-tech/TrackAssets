import { useMutation, useQueryClient } from '@tanstack/react-query';
import api from '../services/api';

export const useCreateGRN = () => {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (payload: { po_id: number; items: any[]; invoice_number?: string; delivery_note_number?: string; }) => {
      const res = await api.post('/receiving/goods-receipts', payload);
      return res.data;
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['purchase_orders'] });
      qc.invalidateQueries({ queryKey: ['inventory'] });
      qc.invalidateQueries({ queryKey: ['dashboard-summary'] });
    },
  });
};

export const useCreateIAR = () => {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (payload: { grn_id: number; status: string; remarks?: string }) => {
      const res = await api.post('/receiving/inspection-reports', payload);
      return res.data;
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['inventory'] });
      qc.invalidateQueries({ queryKey: ['purchase_orders'] });
    },
  });
};

export const useApproveGRN = () => {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (grnId: number) => {
      const res = await api.put(`/receiving/goods-receipts/${grnId}/approve`);
      return res.data;
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['inventory'] });
      qc.invalidateQueries({ queryKey: ['purchase_orders'] });
      qc.invalidateQueries({ queryKey: ['dashboard-summary'] });
    },
  });
};

export default null;
