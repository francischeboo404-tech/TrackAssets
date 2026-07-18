import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import api from '../services/api';

export function useItemTypes() {
  return useQuery({
    queryKey: ['item-types'],
    queryFn: async () => {
      const response = await api.get('/item-types');
      return response.data;
    },
  });
}

export function useCreateItemType() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (data: { name: string; description?: string }) => {
      const response = await api.post('/item-types', data);
      return response.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['item-types'] });
    },
  });
}
