import { useEffect } from 'react';
import { useQueryClient } from '@tanstack/react-query';
import { useToast } from '../context/ToastContext';
import { useAuth } from '../context/AuthContext';
import { useLiveTracking } from '../context/LiveTrackingContext';
import { baseWithApi } from '../services/api';
import { getAccessToken } from '../lib/authStorage';

export const useSSE = () => {
  const queryClient = useQueryClient();
  const { addToast } = useToast();
  const { user } = useAuth();
  const { updatePosition } = useLiveTracking();

  useEffect(() => {
    if (!user) return; // Only connect if authenticated

    const token = getAccessToken();
    const sseUrl = baseWithApi.replace(/\/+$/, '') + '/analytics/stream' + (token ? `?access_token=${encodeURIComponent(token)}` : '');

    let eventSource: EventSource | null = null;
    let retryTimeout: number | null = null;
    let mounted = true;

    const handleMessage = (event: MessageEvent) => {
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
          case 'ITEM_ISSUED':
          case 'ITEM_RETURNED':
            queryClient.invalidateQueries({ queryKey: ['inventory'] });
            queryClient.invalidateQueries({ queryKey: ['dashboard-summary'] });
            queryClient.invalidateQueries({ queryKey: ['dashboard-movements'] });
            queryClient.invalidateQueries({ queryKey: ['item-movements'] });
            queryClient.invalidateQueries({ queryKey: ['audit-logs'] });
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
            if (payload.data.lat && payload.data.lon) {
              updatePosition({
                item_type: payload.data.type,
                item_id: payload.data.item_id,
                lat: payload.data.lat,
                lon: payload.data.lon,
                action: payload.data.action,
                timestamp: payload.data.timestamp,
                warehouse_id: payload.data.warehouse_id,
              });
            }
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

    const connect = async () => {
      if (!mounted) return;

      try {
        console.log('Probing SSE endpoint:', sseUrl);
        const res = await fetch(sseUrl, {
          method: 'GET',
          headers: { Accept: 'text/event-stream' },
          credentials: 'include',
        });

        if (!mounted) return;

        if (!res.ok) {
          console.warn('SSE probe failed, status:', res.status);
          if (retryTimeout) window.clearTimeout(retryTimeout);
          retryTimeout = window.setTimeout(connect, 5000);
          return;
        }

        console.log('SSE probe successful, opening EventSource');
        eventSource = new EventSource(sseUrl, { withCredentials: true } as any);

        eventSource.onopen = () => {
          console.log('SSE connection opened');
          if (retryTimeout) {
            window.clearTimeout(retryTimeout);
            retryTimeout = null;
          }
        };

        eventSource.onmessage = handleMessage;

        eventSource.onerror = (err) => {
          console.error('SSE connection error:', err);
          try {
            eventSource?.close();
          } catch (e) {
            // ignore
          }
          eventSource = null;
          if (mounted) {
            retryTimeout = window.setTimeout(connect, 5000);
          }
        };
      } catch (err) {
        console.error('SSE probe error:', err);
        if (mounted) {
          if (retryTimeout) window.clearTimeout(retryTimeout);
          retryTimeout = window.setTimeout(connect, 5000);
        }
      }
    };

    connect();

    return () => {
      mounted = false;
      if (retryTimeout) window.clearTimeout(retryTimeout);
      try {
        eventSource?.close();
      } catch (e) {
        // ignore
      }
    };
  }, [queryClient, addToast, updatePosition, user]);
};
