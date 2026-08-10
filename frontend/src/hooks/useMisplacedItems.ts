import { useQuery, useQueryClient } from '@tanstack/react-query';
import api from '../services/api';

export interface MisplacedItem {
  type: 'MISPLACED_ITEM';
  severity: 'HIGH' | 'MEDIUM' | 'LOW';
  item_type: 'asset' | 'inventory' | 'inventory_instance';
  item_id: number;
  item_name: string;
  item_code: string;
  expected_location: {
    warehouse_id: number;
    warehouse_name: string;
    bin_id?: number;
  };
  actual_location: {
    warehouse_id: number;
    warehouse_name: string;
    bin_id?: number;
    timestamp?: string;
  };
  days_since_scan?: number;
  message: string;
  assignment_type?: string;
}

export interface MisplacedItemsResponse {
  misplaced_items: MisplacedItem[];
  count: number;
  total?: number;
}

export const useMisplacedItems = (options?: {
  limit?: number;
  enabled?: boolean;
  refetchInterval?: number;
}) => {
  const limit = options?.limit || 50;
  const enabled = options?.enabled !== false;
  const refetchInterval = options?.refetchInterval || 60000; // 1 minute default

  return useQuery({
    queryKey: ['misplaced-items', limit],
    queryFn: async () => {
      try {
        // Try to fetch from on-demand endpoint (Phase 4: Option A)
        const response = await api.get<MisplacedItemsResponse>(
          `/tracking/misplaced-items?limit=${limit}`,
        );
        return response.data.misplaced_items;
      } catch (error) {
        // Fallback: return empty array if endpoint not available
        // In production, this would be the main endpoint
        console.warn('Misplaced items endpoint not available:', error);
        return [];
      }
    },
    enabled,
    refetchInterval,
    staleTime: 30000, // 30 seconds
  });
};

export const useMisplacedItemsFiltered = (options?: {
  severity?: 'HIGH' | 'MEDIUM' | 'LOW';
  itemType?: 'asset' | 'inventory' | 'inventory_instance';
  daysThreshold?: number;
  enabled?: boolean;
}) => {
  const queryClient = useQueryClient();
  const { data: allItems = [], isLoading, error } = useMisplacedItems({ enabled: options?.enabled });

  // Filter in-memory on the client
  const filtered = allItems.filter((item) => {
    if (options?.severity && item.severity !== options.severity) {
      return false;
    }
    if (options?.itemType && item.item_type !== options.itemType) {
      return false;
    }
    if (options?.daysThreshold && item.days_since_scan) {
      if (item.days_since_scan < options.daysThreshold) {
        return false;
      }
    }
    return true;
  });

  return {
    data: filtered,
    isLoading,
    error,
    count: filtered.length,
    highSeverityCount: filtered.filter((i) => i.severity === 'HIGH').length,
    mediumSeverityCount: filtered.filter((i) => i.severity === 'MEDIUM').length,
    lowSeverityCount: filtered.filter((i) => i.severity === 'LOW').length,
  };
};

export const useMisplacedItemsByItemType = (itemType: 'asset' | 'inventory' | 'inventory_instance') => {
  return useMisplacedItemsFiltered({ itemType });
};

export const useMisplacedItemsBySeverity = (severity: 'HIGH' | 'MEDIUM' | 'LOW') => {
  return useMisplacedItemsFiltered({ severity });
};

export const useMisplacedItemsStats = () => {
  const { data: allItems = [], isLoading } = useMisplacedItems();

  return {
    total: allItems.length,
    highSeverity: allItems.filter((i) => i.severity === 'HIGH').length,
    mediumSeverity: allItems.filter((i) => i.severity === 'MEDIUM').length,
    lowSeverity: allItems.filter((i) => i.severity === 'LOW').length,
    isLoading,
    percentageHigh: allItems.length > 0
      ? Math.round((allItems.filter((i) => i.severity === 'HIGH').length / allItems.length) * 100)
      : 0,
  };
};
