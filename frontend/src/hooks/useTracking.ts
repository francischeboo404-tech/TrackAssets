import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import api from '../services/api';

export interface ScanEventRecord {
  id: number;
  timestamp: string;
  action: string;
  user_id: number;
  user_role?: string;
  warehouse_id?: number;
  bin_id?: number;
  latitude?: number;
  longitude?: number;
  previous_state?: Record<string, unknown>;
  new_state?: Record<string, unknown>;
  validation_status: string;
  notes?: string;
}

export const useEntityQr = (
  entityType: 'asset' | 'inventory',
  entityId?: number,
) => {
  return useQuery({
    queryKey: ['entity-qr', entityType, entityId],
    queryFn: async () => {
      const response = await api.get(
        `/tracking/qr/${entityType}/${entityId}`,
      );
      return response.data as {
        signed_token: string;
        scan_url: string;
        entity_code: string;
      };
    },
    enabled: !!entityId,
    staleTime: 60_000,
  });
};

export const useAllowedScanActions = () => {
  return useQuery({
    queryKey: ['tracking-allowed-actions'],
    queryFn: async () => {
      const response = await api.get<{ role: string; actions: string[] }>(
        '/tracking/allowed-actions',
      );
      return response.data;
    },
  });
};

export const useTrackingHistory = (
  itemType?: string,
  itemId?: number,
) => {
  return useQuery({
    queryKey: ['item-history', itemType, itemId],
    queryFn: async () => {
      const response = await api.get<{
        history: ScanEventRecord[];
      }>(`/tracking/history/${itemType}/${itemId}`);
      return response.data.history;
    },
    enabled: !!itemType && !!itemId,
  });
};

export const useRecordScan = () => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (payload: {
      qr_data: string;
      action_type: string;
      warehouse_id?: number;
      bin_id?: number;
      notes?: string;
      lat?: number;
      lon?: number;
    }) => {
      const response = await api.post('/tracking/scan', payload);
      return response.data;
    },
    onSuccess: (data) => {
      const item = data?.item;
      if (item?.type && item?.id) {
        queryClient.invalidateQueries({
          queryKey: ['item-history', item.type, item.id],
        });
      }
      queryClient.invalidateQueries({ queryKey: ['assets'] });
      queryClient.invalidateQueries({ queryKey: ['inventory'] });
      queryClient.invalidateQueries({ queryKey: ['dashboard-summary'] });
    },
  });
};

export const useVerifyScan = () => {
  return useMutation({
    mutationFn: async (qr_data: string) => {
      const response = await api.post('/tracking/scan/verify', { qr_data });
      return response.data;
    },
  });
};
