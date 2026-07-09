/**
 * WarehouseContext — Global warehouse selection state.
 *
 * Responsibilities:
 *   - Fetch all warehouses for the org on mount.
 *   - Expose the "active" warehouse (null = All Warehouses aggregated view).
 *   - Persist active warehouse selection in localStorage so it survives refresh.
 *   - Provide setActiveWarehouse() to any component in the tree.
 */

import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
} from 'react';
import type { ReactNode } from 'react';
import { useQuery } from '@tanstack/react-query';
import api from '../services/api';
import { useAuth } from './AuthContext';

// ──────────────────────────────────────────────────────────────────────────────
// Types
// ──────────────────────────────────────────────────────────────────────────────

export interface WarehouseSummary {
  id: number;
  name: string;
  code: string;
  address?: string | null;
  is_active: boolean;
  is_main_warehouse: boolean;
  warehouse_type: 'main' | 'branch';
  hierarchy_level: number;
  parent_warehouse_id?: number | null;
  total_bins: number;
  occupied_bins: number;
  empty_bins: number;
  utilization_percentage: number;
}

interface WarehouseContextValue {
  /** All warehouses for this organisation */
  warehouses: WarehouseSummary[];
  /** Currently selected warehouse; null = "All Warehouses" view */
  activeWarehouse: WarehouseSummary | null;
  /** The main (headquarters) warehouse if one exists */
  mainWarehouse: WarehouseSummary | null;
  /** True while warehouses are being loaded */
  isLoading: boolean;
  /** Set active warehouse; pass null to show aggregated org-wide view */
  setActiveWarehouse: (warehouse: WarehouseSummary | null) => void;
  /** The active warehouse_id (undefined when "All Warehouses") */
  activeWarehouseId: number | undefined;
}

// ──────────────────────────────────────────────────────────────────────────────
// Constants
// ──────────────────────────────────────────────────────────────────────────────

const STORAGE_KEY = 'trackit:active_warehouse_id';

// ──────────────────────────────────────────────────────────────────────────────
// Context creation
// ──────────────────────────────────────────────────────────────────────────────

const WarehouseContext = createContext<WarehouseContextValue>({
  warehouses: [],
  activeWarehouse: null,
  mainWarehouse: null,
  isLoading: false,
  setActiveWarehouse: () => {},
  activeWarehouseId: undefined,
});

// ──────────────────────────────────────────────────────────────────────────────
// Provider
// ──────────────────────────────────────────────────────────────────────────────

export function WarehouseProvider({ children }: { children: ReactNode }) {
  const [activeWarehouse, setActiveWarehouseState] = useState<WarehouseSummary | null>(null);
  const { user } = useAuth();

  // Load warehouses for this org
  const { data: warehouses = [], isLoading } = useQuery<WarehouseSummary[]>({
    queryKey: ['warehouses'],
    queryFn: async () => {
      const res = await api.get<WarehouseSummary[]>('/warehouses');
      return res.data;
    },
    enabled: !!user,
    staleTime: 60_000,
    refetchInterval: 120_000,
  });

  // Restore persisted selection once warehouses are loaded
  useEffect(() => {
    if (isLoading || warehouses.length === 0) return;

    const saved = localStorage.getItem(STORAGE_KEY);
    if (saved !== null) {
      const savedId = Number(saved);
      const found = warehouses.find((w) => w.id === savedId) ?? null;
      setActiveWarehouseState(found);
    }
    // Only run on initial load
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [isLoading]);

  const mainWarehouse = useMemo(
    () => warehouses.find((w) => w.is_main_warehouse) ?? warehouses[0] ?? null,
    [warehouses],
  );

  const setActiveWarehouse = useCallback((warehouse: WarehouseSummary | null) => {
    setActiveWarehouseState(warehouse);
    if (warehouse === null) {
      localStorage.removeItem(STORAGE_KEY);
    } else {
      localStorage.setItem(STORAGE_KEY, String(warehouse.id));
    }
  }, []);

  const value = useMemo<WarehouseContextValue>(
    () => ({
      warehouses,
      activeWarehouse,
      mainWarehouse,
      isLoading,
      setActiveWarehouse,
      activeWarehouseId: activeWarehouse?.id,
    }),
    [warehouses, activeWarehouse, mainWarehouse, isLoading, setActiveWarehouse],
  );

  return (
    <WarehouseContext.Provider value={value}>
      {children}
    </WarehouseContext.Provider>
  );
}

// ──────────────────────────────────────────────────────────────────────────────
// Hook
// ──────────────────────────────────────────────────────────────────────────────

/** Returns the global warehouse context. */
export function useWarehouse(): WarehouseContextValue {
  return useContext(WarehouseContext);
}

/** Convenience hook: returns just the active warehouse_id (number | undefined). */
export function useActiveWarehouseId(): number | undefined {
  return useContext(WarehouseContext).activeWarehouseId;
}
