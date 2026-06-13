import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import api from '../services/api';
import { useToast } from '../context/ToastContext';

export interface Department {
  id: number;
  name: string;
  code: string;
  description: string;
  head?: {
    id: number;
    username: string;
    first_name: string;
    last_name: string;
  };
  asset_count: number;
}

export const useDepartments = (params: any = {}) => {
  return useQuery({
    queryKey: ['departments', params],
    queryFn: async () => {
      const response = await api.get<{ departments: Department[], pagination: any }>('/departments', { params });
      return Array.isArray(response.data) ? response.data : response.data.departments;
    },
  });
};

export const useCreateDepartment = () => {
  const queryClient = useQueryClient();
  const { addToast } = useToast();

  return useMutation({
    mutationFn: async (data: Partial<Department> & { head_id?: number | null }) => {
      const response = await api.post<{ message: string; department_id: number }>('/departments', data);
      return response.data;
    },
    onSuccess: () => {
      addToast('success', 'Department Created', 'The department was created successfully.');
      queryClient.invalidateQueries({ queryKey: ['departments'] });
    },
    onError: (error: any) => {
      addToast('error', 'Creation Failed', error.response?.data?.message || 'Could not create department.');
    },
  });
};

export const useUpdateDepartment = () => {
  const queryClient = useQueryClient();
  const { addToast } = useToast();

  return useMutation({
    mutationFn: async ({ id, data }: { id: number; data: Partial<Department> & { head_id?: number | null } }) => {
      const response = await api.put<{ message: string }>(`/departments/${id}`, data);
      return response.data;
    },
    onSuccess: () => {
      addToast('success', 'Department Updated', 'The department was updated successfully.');
      queryClient.invalidateQueries({ queryKey: ['departments'] });
    },
    onError: (error: any) => {
      addToast('error', 'Update Failed', error.response?.data?.message || 'Could not update department.');
    },
  });
};

export const useDeleteDepartment = () => {
  const queryClient = useQueryClient();
  const { addToast } = useToast();

  return useMutation({
    mutationFn: async (id: number) => {
      const response = await api.delete<{ message: string }>(`/departments/${id}`);
      return response.data;
    },
    onSuccess: () => {
      addToast('success', 'Department Deleted', 'The department was permanently removed.');
      queryClient.invalidateQueries({ queryKey: ['departments'] });
    },
    onError: (error: any) => {
      addToast('error', 'Deletion Failed', error.response?.data?.message || 'Could not delete department. It may have assets assigned.');
    },
  });
};
