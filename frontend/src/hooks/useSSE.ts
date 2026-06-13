import { useEffect } from 'react';
import { useQueryClient } from '@tanstack/react-query';
import { useToast } from '../context/ToastContext';
import { useAuth } from '../context/AuthContext';
import { baseWithApi } from '../services/api';

export const useSSE = () => {
  const queryClient = useQueryClient();
  const { addToast } = useToast();
  const { user } = useAuth();

  useEffect(() => {
    if (!user) return; // Only connect if authenticated

    const sseUrl = baseWithApi.replace(/\/+$/, '') + '/analytics/stream';
    const eventSource = new EventSource(sseUrl, { withCredentials: true } as any);

    eventSource.onmessage = (event) => {
      try {
        const payload = JSON.parse(event.data);
        console.log('Real-time event received:', payload);

        // Map events to cache invalidation
        switch (payload.type) {
          case 'STOCK_UPDATE':
            queryClient.invalidateQueries({ queryKey: ['inventory'] });
            queryClient.invalidateQueries({ queryKey: ['dashboard-summary'] });
            queryClient.invalidateQueries({ queryKey: ['dashboard-movements'] });
            break;
          case 'NEW_ALERT':
          case 'RESTOCK_ALERT':
            queryClient.invalidateQueries({ queryKey: ['active-alerts'] });
            queryClient.invalidateQueries({ queryKey: ['dashboard-summary'] });
            addToast('warning', 'Low Stock Alert', payload.data?.message || 'An item has reached critical levels.');
            break;
          case 'ASSET_TRANSFER':
            queryClient.invalidateQueries({ queryKey: ['transfer-requests'] });
            queryClient.invalidateQueries({ queryKey: ['transfer-stats'] });
            queryClient.invalidateQueries({ queryKey: ['assets'] });
            queryClient.invalidateQueries({ queryKey: ['inventory'] });
            queryClient.invalidateQueries({ queryKey: ['dashboard-summary'] });
            break;
          case 'SCAN_EVENT':
            queryClient.invalidateQueries({ queryKey: ['item-history', payload.data.type, payload.data.item_id] });
            queryClient.invalidateQueries({ queryKey: ['assets'] });
            queryClient.invalidateQueries({ queryKey: ['inventory'] });
            queryClient.invalidateQueries({ queryKey: ['dashboard-summary'] });
            queryClient.invalidateQueries({ queryKey: ['dashboard-movements'] });
            addToast('info', 'Real-time Scan', `New activity detected for ${payload.data.type} #${payload.data.item_id}`);
            break;
          case 'AUDIT_CREATED':
            queryClient.invalidateQueries({ queryKey: ['audit-logs'] });
            break;
          case 'ORGANIZATION_UPDATE':
            queryClient.invalidateQueries({ queryKey: ['settings', 'organization'] });
            addToast('info', 'Settings Updated', 'Organizational settings have been updated.');
            break;
          case 'ASSET_CREATED':
          case 'ASSET_UPDATED':
          case 'ASSET_STATUS_CHANGED':
          case 'ASSET_DELETED':
            queryClient.invalidateQueries({ queryKey: ['assets'] });
            queryClient.invalidateQueries({ queryKey: ['dashboard-summary'] });
            queryClient.invalidateQueries({ queryKey: ['dashboard-movements'] });
            break;
          case 'INVENTORY_CREATED':
          case 'INVENTORY_UPDATED':
          case 'INVENTORY_DELETED':
            queryClient.invalidateQueries({ queryKey: ['inventory'] });
            queryClient.invalidateQueries({ queryKey: ['dashboard-summary'] });
            queryClient.invalidateQueries({ queryKey: ['dashboard-movements'] });
            break;
          case 'WAREHOUSE_UPDATED':
            queryClient.invalidateQueries({ queryKey: ['warehouses'] });
            break;
          case 'DEPARTMENT_UPDATED':
            queryClient.invalidateQueries({ queryKey: ['departments'] });
            break;
          default:
            console.warn('Unknown event type:', payload.type);
        }
      } catch (err) {
        console.error('Error parsing SSE event:', err);
      }
    };

    eventSource.onerror = (err) => {
      console.error('SSE connection error:', err);
      eventSource.close();
    };

    return () => {
      eventSource.close();
    };
  }, [queryClient, addToast]);
};
