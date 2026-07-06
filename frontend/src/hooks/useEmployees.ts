import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { listEmployees, createEmployee, updateEmployee, deleteEmployee } from '../services/employees';
import { useToast } from '../context/ToastContext';

export const useEmployees = (params: any = {}) => {
  return useQuery({
    queryKey: ['employees', params],
    queryFn: async () => {
      const response = await listEmployees(params);
      // If paginated params provided, return full response (employees + pagination), else return array for backwards compatibility
      if (params.page || params.per_page) return response;
      return response.employees || response;
    },
  });
};

export const useCreateEmployee = () => {
  const queryClient = useQueryClient();
  const { addToast } = useToast();

  return useMutation({
    mutationFn: async (payload: any) => createEmployee(payload),
    onMutate: async (newEmp: any) => {
      await queryClient.cancelQueries({ queryKey: ['employees'] });
      const previous = queryClient.getQueryData(['employees']);
      const optimistic = { id: `temp-${Date.now()}`, ...newEmp };
      queryClient.setQueryData(['employees'], (old: any) => old ? [optimistic, ...old] : [optimistic]);
      return { previous };
    },
    onError: (err: any, _newEmp: any, context: any) => {
      addToast('error', 'Failed to create employee', err.response?.data?.message || err.message);
      if (context?.previous) {
        queryClient.setQueryData(['employees'], context.previous);
      }
    },
    onSettled: () => {
      addToast('success', 'Employee created');
      queryClient.invalidateQueries({ queryKey: ['employees'] });
    },
  });
};

export const useUpdateEmployee = () => {
  const queryClient = useQueryClient();
  const { addToast } = useToast();

  return useMutation({
    mutationFn: async ({ id, data }: { id: number; data: any }) => updateEmployee(id, data),
    onMutate: async ({ id, data }: { id: number; data: any }) => {
      await queryClient.cancelQueries({ queryKey: ['employees'] });
      const previous = queryClient.getQueryData(['employees']);
      queryClient.setQueryData(['employees'], (old: any) => {
        if (!old) return old;
        return old.map((e: any) => e.id === id ? { ...e, ...data } : e);
      });
      return { previous };
    },
    onError: (err: any, _vars: any, context: any) => {
      addToast('error', 'Failed to update employee', err.response?.data?.message || err.message);
      if (context?.previous) {
        queryClient.setQueryData(['employees'], context.previous);
      }
    },
    onSettled: () => {
      addToast('success', 'Employee updated');
      queryClient.invalidateQueries({ queryKey: ['employees'] });
    },
  });
};

export const useDeleteEmployee = () => {
  const queryClient = useQueryClient();
  const { addToast } = useToast();

  return useMutation({
    mutationFn: async (id: number) => deleteEmployee(id),
    onMutate: async (id: number) => {
      await queryClient.cancelQueries({ queryKey: ['employees'] });
      const previous = queryClient.getQueryData(['employees']);
      queryClient.setQueryData(['employees'], (old: any) => old ? old.filter((e: any) => e.id !== id) : old);
      return { previous };
    },
    onError: (err: any, _id: any, context: any) => {
      addToast('error', 'Failed to delete employee', err.response?.data?.message || err.message);
      if (context?.previous) {
        queryClient.setQueryData(['employees'], context.previous);
      }
    },
    onSettled: () => {
      addToast('success', 'Employee deleted');
      queryClient.invalidateQueries({ queryKey: ['employees'] });
    },
  });
};
