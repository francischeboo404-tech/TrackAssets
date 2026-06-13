import { useQuery } from '@tanstack/react-query';
import api from '../services/api';

export interface SearchResult {
  id: number;
  name: string;
  code: string;
  type: string;
}

export interface SearchResponse {
  assets: SearchResult[];
  inventory: SearchResult[];
  users: SearchResult[];
  departments: SearchResult[];
}

export const useGlobalSearch = (query: string) => {
  return useQuery({
    queryKey: ['global-search', query],
    queryFn: async () => {
      if (!query || query.length < 2) {
        return { assets: [], inventory: [], users: [], departments: [] } as SearchResponse;
      }
      const response = await api.get<SearchResponse>(`/search/?q=${encodeURIComponent(query)}`);
      return response.data;
    },
    enabled: query.length >= 2,
    staleTime: 1000 * 60 * 5, // 5 minutes
  });
};
