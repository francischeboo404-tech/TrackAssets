import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import api from '../services/api';

export interface TransferRequest {
  id: number;
  transfer_type: 'employee_to_employee' | 'department_to_department' | 'warehouse_to_warehouse';
  asset_id: number;
  asset_code: string;
  asset_name: string;
  from_department_name: string;
  to_department_name: string;
  from_user_id?: number;
  from_user_name?: string;
  to_user_id?: number;
  to_user_name?: string;
  requested_location: string;
  comment: string;
  status: 'pending' | 'approved' | 'in_transit' | 'completed' | 'rejected';
  requested_by: string;
  requested_at: string;
}

export interface TransferRequestPayload {
  transfer_type: 'employee_to_employee' | 'department_to_department' | 'warehouse_to_warehouse';
  asset_id: number;
  item_type?: 'asset' | 'inventory';
  to_user_id?: number;
  new_department_id?: number;
  from_department_id?: number;
  to_warehouse_id?: number;
  to_bin_id?: number;
  new_location?: string;
  comment?: string;
}

export const useTransferRequests = (status: 'all' | 'pending' | 'approved' | 'in_transit' | 'completed' | 'rejected' = 'pending', page = 1, search?: string, departmentId?: number) => {
  return useQuery({
    queryKey: ['transfer-requests', status, page, search, departmentId],
    queryFn: async () => {
      const params: any = { status, page };
      if (search) params.search = search;
      if (departmentId) params.department_id = departmentId;
      const response = await api.get<{ transfer_requests: TransferRequest[], pagination: any }>('/transfers/requests', {
        params
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
      queryClient.invalidateQueries({ queryKey: ['transfer-stats'] });
      queryClient.invalidateQueries({ queryKey: ['assets'] });
    },
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
      queryClient.invalidateQueries({ queryKey: ['transfer-stats'] });
    },
  });
};

export const useRequestTransfer = () => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (data: TransferRequestPayload) => {
      const response = await api.post('/transfers/request', data);
      return response.data;
    },
    onSuccess: (_, variables) => {
      queryClient.invalidateQueries({ queryKey: ['transfer-requests'] });
      queryClient.invalidateQueries({ queryKey: ['transfer-stats'] });
      queryClient.invalidateQueries({ queryKey: ['assets'] });
      queryClient.invalidateQueries({ queryKey: ['asset', variables.asset_id] });
      queryClient.invalidateQueries({ queryKey: ['dashboard-summary'] });
    },
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
      queryClient.invalidateQueries({ queryKey: ['transfer-stats'] });
      queryClient.invalidateQueries({ queryKey: ['assets'] });
    },
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
      queryClient.invalidateQueries({ queryKey: ['transfer-stats'] });
      queryClient.invalidateQueries({ queryKey: ['assets'] });
      queryClient.invalidateQueries({ queryKey: ['dashboard-summary'] });
    },
  });
};
