import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import api from '../services/api';

export interface InternalUser {
  id: number;
  username: string;
  email: string;
  role: string;
  is_active: boolean;
  last_login: string | null;
  first_name?: string;
  last_name?: string;
}

export const useUsers = (params: { page?: number; role?: string; q?: string; search?: string } = {}) => {
  return useQuery({
    queryKey: ['users', params],
    queryFn: async () => {
      const { search, ...rest } = params;
      const apiParams = { ...rest, q: rest.q || search };
      const response = await api.get<{ users: InternalUser[], pagination: any }>('/users', { params: apiParams });
      return response.data;
    }
  });
};

export const useUpdateUserRole = () => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async ({ id, role }: { id: number; role: string }) => {
      const response = await api.put(`/users/${id}/role`, { role });
      return response.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['users'] });
    }
  });
};

export const useToggleUserStatus = () => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async ({ id, is_active }: { id: number; is_active: boolean }) => {
      const response = await api.put(`/users/${id}/status`, { is_active });
      return response.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['users'] });
    }
  });
};
