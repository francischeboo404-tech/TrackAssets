import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import api from '../services/api';

export const useRequisitions = (params: any = {}) => {
  return useQuery({
    queryKey: ['requisitions', params],
    queryFn: async () => {
      const res = await api.get('/requisition/issue-slips', { params });
      return res.data;
    },
  });
};

export const useCreateRequisition = () => {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (payload: { items: any[]; warehouse_id?: number | null }) => {
      // forward warehouse_id if provided; backend will ignore unknown keys if not supported
      const res = await api.post('/requisition/requisitions', payload);
      return res.data;
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['requisitions'] });
      qc.invalidateQueries({ queryKey: ['inventory'] });
      qc.invalidateQueries({ queryKey: ['dashboard-summary'] });
    },
  });
};

export const useApproveRequisition = () => {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (id: number) => {
      const res = await api.put(`/requisition/issue-slips/${id}/approve`);
      return res.data;
    },
    onSuccess: () => qc.invalidateQueries({ queryKey: ['requisitions'] }),
  });
};

export const useIssueRequisition = () => {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (id: number) => {
      const res = await api.put(`/requisition/issue-slips/${id}/issue`);
      return res.data;
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['requisitions'] });
      qc.invalidateQueries({ queryKey: ['inventory'] });
      qc.invalidateQueries({ queryKey: ['dashboard-summary'] });
    },
  });
};

export const useCancelRequisition = () => {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async ({ id, reason }: { id: number; reason?: string }) => {
      const res = await api.post(`/requisition/issue-slips/${id}/cancel`, { reason });
      return res.data;
    },
    onSuccess: () => qc.invalidateQueries({ queryKey: ['requisitions'] }),
  });
};

export default null;
