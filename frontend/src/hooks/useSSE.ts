import { useEffect, useRef, useCallback } from 'react';
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

  const eventSourceRef = useRef<EventSource | null>(null);
  const retryCountRef = useRef(0);
  const retryTimeoutRef = useRef<NodeJS.Timeout | null>(null);
  const isManualCloseRef = useRef(false);

  const MAX_RETRIES = 10;
  const BASE_RETRY_DELAY = 1000; // 1 second
  const MAX_RETRY_DELAY = 30000; // 30 seconds

  // Calculate exponential backoff delay
  const getRetryDelay = (attemptNumber: number): number => {
    const delay = Math.min(
      BASE_RETRY_DELAY * Math.pow(2, attemptNumber - 1),
      MAX_RETRY_DELAY
    );
    // Add jitter (±10%) to prevent thundering herd
    const jitter = delay * 0.1 * (Math.random() - 0.5);
    return Math.max(100, delay + jitter);
  };

  const connectSSE = useCallback(() => {
    if (isManualCloseRef.current || !user) return;
    if (eventSourceRef.current) return; // Already connecting/connected

    const sseUrl = `${baseWithApi.replace(/\/+$/, '')}/analytics/stream?access_token=${getAccessToken() || ''}`;
    const eventSource = new EventSource(sseUrl, { withCredentials: true } as any);

    eventSourceRef.current = eventSource;

    eventSource.onmessage = (event) => {
      try {
        // Reset retry counter on successful connection
        if (retryCountRef.current > 0) {
          retryCountRef.current = 0;
          addToast('success', 'Connection Restored', 'Real-time updates resumed.');
        }

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
          case 'SCAN_ANOMALY_DETECTED':
            // Real-time scan anomalies (impossible travel, etc.)
            const anomalySeverity = payload.data?.severity || 'MEDIUM';
            const anomalyType = payload.data?.type || 'Unknown Anomaly';
            const anomalyToastType = anomalySeverity === 'HIGH' ? 'error' : 'warning';
            addToast(anomalyToastType, `Security Alert: ${anomalyType}`, payload.data?.message || 'An anomaly was detected during scan');
            break;
          case 'MISPLACED_ITEM_DETECTED':
            // Real-time misplaced items alerts via SSE
            queryClient.invalidateQueries({ queryKey: ['misplaced-items'] });
            const severity = payload.data?.severity || 'MEDIUM';
            const itemName = payload.data?.item_name || 'Unknown Item';
            const toastType = severity === 'HIGH' ? 'error' : severity === 'MEDIUM' ? 'warning' : 'info';
            const toastMessage = payload.data?.message || `${itemName} may be misplaced`;
            addToast(toastType, `${severity} Priority: Misplaced Item`, toastMessage);
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

      // Close the failed connection
      eventSource.close();
      eventSourceRef.current = null;

      // Don't retry if manually closed
      if (isManualCloseRef.current) return;

      retryCountRef.current += 1;

      if (retryCountRef.current > MAX_RETRIES) {
        addToast(
          'error',
          'Real-time Connection Failed',
          'Unable to establish real-time connection after multiple attempts. Please refresh the page.'
        );
        console.error('SSE connection failed after max retries');
        return;
      }

      const retryDelay = getRetryDelay(retryCountRef.current);
      const retrySeconds = (retryDelay / 1000).toFixed(1);

      addToast(
        'warning',
        'Real-time Connection Lost',
        `Reconnecting in ${retrySeconds}s... (Attempt ${retryCountRef.current}/${MAX_RETRIES})`
      );

      console.log(
        `SSE reconnection attempt ${retryCountRef.current}/${MAX_RETRIES} in ${retryDelay}ms`
      );

      // Schedule reconnection with exponential backoff
      retryTimeoutRef.current = setTimeout(() => {
        connectSSE();
      }, retryDelay);
    };
  }, [user, addToast]);

  useEffect(() => {
    if (!user) {
      isManualCloseRef.current = true;
      if (eventSourceRef.current) {
        eventSourceRef.current.close();
        eventSourceRef.current = null;
      }
      return;
    }

    isManualCloseRef.current = false;
    retryCountRef.current = 0;
    connectSSE();

    return () => {
      // Cleanup on unmount
      isManualCloseRef.current = true;
      if (retryTimeoutRef.current) {
        clearTimeout(retryTimeoutRef.current);
      }
      if (eventSourceRef.current) {
        eventSourceRef.current.close();
        eventSourceRef.current = null;
      }
    };
  }, [connectSSE, user]);
};
