/**
 * Core enterprise entity types for TrackIT
 */

export type UserRole = 'admin' | 'staff' | 'viewer' | 'auditor' | 'dept_head' | 'store_manager';

export interface User {
  id: number;
  username: string;
  email: string;
  role: UserRole;
  organisation_id: number;
}

export interface InventoryItem {
  id: number;
  organisation_id: number;
  name: string;
  sku: string;
  description?: string;
  quantity: number;
  reorder_level: number;
  unit_price: number;
  unit: string;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

export interface Asset {
  id: number;
  organisation_id: number;
  asset_code: string;
  name: string;
  type: string;
  status: 'requested' | 'approved' | 'rejected' | 'in_use' | 'maintenance' | 'disposed';
  condition: 'new' | 'good' | 'fair' | 'repair' | 'condemned';
  purchase_date: string;
  purchase_value: number;
  useful_life: number;
  current_value: number;
  location?: string;
  department_id?: number;
  department_name?: string;
  serial_number?: string;
  warehouse_id?: number;
  bin_id?: number;
}

export interface Warehouse {
  id: number;
  organisation_id: number;
  name: string;
  code: string;
  location?: string;
  is_active: boolean;
}

export interface WarehouseUtilization {
  warehouse_id: number;
  warehouse_name: string;
  total_bins: number;
  occupied_bins: number;
  utilization_percentage: number;
  empty_bins: number;
}

export interface RestockAlert {
  id: number;
  organisation_id: number;
  item_id: number;
  item_name: string;
  warehouse_id?: number;
  severity: 'LOW' | 'CRITICAL' | 'OUT_OF_STOCK';
  current_quantity: number;
  threshold_level: number;
  message: string;
  status: 'PENDING' | 'RESOLVED';
  created_at: string;
}

export interface StockUpdate {
  id: string;
  quantity: number;
  type: 'IN' | 'OUT';
  reference: string;
  notes?: string;
}

export interface AuditLog {
  id: string;
  user_id: string;
  username: string;
  action: string;
  entity_type: string;
  entity_id: string;
  context?: Record<string, any>;
  details?: any;
  ip_address?: string;
  created_at: string;
}
