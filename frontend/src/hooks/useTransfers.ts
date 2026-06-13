import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import api from '../services/api';

export interface TransferRequest {
  id: number;
  asset_id: number;
  asset_code: string;
  asset_name: string;
  from_department_name: string;
  to_department_name: string;
  requested_location: string;
  comment: string;
  status: 'pending' | 'approved' | 'in_transit' | 'completed' | 'rejected';
  requested_by: string;
  requested_at: string;
}

export const useTransferRequests = (status: 'all' | 'pending' | 'approved' | 'in_transit' | 'completed' | 'rejected' = 'pending', page = 1, search?: string) => {
  return useQuery({
    queryKey: ['transfer-requests', status, page, search],
    queryFn: async () => {
      const response = await api.get<{ transfer_requests: TransferRequest[], pagination: any }>('/transfers/requests', {
        params: { status, page, search }
      });
      return response.data;
    }
  });
};

export const useTransferStats = () => {
  return useQuery({
    queryKey: ['transfer-stats'],
    queryFn: async () => {
      const response = await api.get<{ pending: number, approved: number, in_transit: number, completed: number, rejected: number, total: number }>('/transfers/stats');
      return response.data;
    }
  });
};

export const useApproveTransfer = () => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async ({ id, comments }: { id: number; comments?: string }) => {
      const response = await api.post(`/transfers/requests/${id}/approve`, { comments });
      return response.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['transfer-requests'] });
      queryClient.invalidateQueries({ queryKey: ['assets'] });
    }
  });
};

export const useRejectTransfer = () => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async ({ id, comments }: { id: number; comments: string }) => {
      const response = await api.post(`/transfers/requests/${id}/reject`, { comments });
      return response.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['transfer-requests'] });
    }
  });
};

export const useRequestTransfer = () => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (data: { asset_id: number; new_department_id: number; new_location?: string; comment?: string; to_warehouse_id?: number; to_bin_id?: number }) => {
      const response = await api.post('/transfers/request', data);
      return response.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['transfer-requests'] });
    }
  });
};

export const useDispatchTransfer = () => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async ({ id }: { id: number }) => {
      const response = await api.post(`/transfers/requests/${id}/dispatch`);
      return response.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['transfer-requests'] });
      queryClient.invalidateQueries({ queryKey: ['assets'] });
    }
  });
};

export const useReceiveTransfer = () => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async ({ id }: { id: number }) => {
      const response = await api.post(`/transfers/requests/${id}/receive`);
      return response.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['transfer-requests'] });
      queryClient.invalidateQueries({ queryKey: ['assets'] });
    }
  });
};
