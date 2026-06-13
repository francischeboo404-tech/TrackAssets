export interface ReportEnvelope<T> {
  success: boolean;
  data: T;
  message: string;
}

export interface StatusSlice {
  code: string;
  label: string;
  count: number;
  percentage: number;
  color: string;
}

export interface AssetsReportData {
  total_count: number;
  by_status: StatusSlice[];
  by_department: { department: string; count: number; percentage: number }[];
  by_location: { location: string; count: number }[];
  utilization_rate: number;
  lifecycle_over_time: Record<string, string | number>[];
  period_days: number;
  scope?: string;
}

export interface InventoryReportData {
  total_skus: number;
  total_units: number;
  total_valuation: number;
  currency: string;
  low_stock_count: number;
  overstock_count: number;
  low_stock_items: { id: number; sku: string; name: string; quantity: number; reorder_level: number }[];
  stock_levels_chart: { sku: string; name: string; quantity: number; unit: string }[];
  movement_over_time: { date: string; inflow: number; outflow: number; net: number }[];
  most_consumed: { id: number; sku: string; name: string; quantity_out: number }[];
  usage_frequency: { sku: string; name: string; frequency: number }[];
  period_days: number;
}

export interface TrackingReportData {
  total_scans: number;
  scans_by_action: { action: string; count: number }[];
  scans_by_role: { role: string; count: number }[];
  actions_per_role: { role: string; count: number }[];
  activity_frequency: { date: string; scans: number }[];
  movement_timeline?: {
    id: number;
    timestamp: string;
    action_type: string;
    item_type: string;
    item_id: number;
    user: string | null;
    role: string;
  }[];
  recent_system_events: { id: number; action: string; entity_type: string; created_at: string }[];
  period_days: number;
}

export interface DashboardReportData {
  kpis: {
    total_assets: number;
    total_inventory_units: number;
    total_skus: number;
    inventory_valuation: number;
    asset_book_value: number;
    total_valuation: number;
    currency: string;
    compliance_score: number;
    utilization_rate: number;
    scan_activity: number;
    low_stock_count: number;
  };
  assets?: AssetsReportData;
  inventory?: InventoryReportData;
  tracking?: TrackingReportData;
  movement_trends?: Record<string, { IN: number; OUT: number }>;
  critical_alerts: { severity: string; title: string; message: string; count: number }[];
  recent_activity?: { id: number; action: string; entity_type: string; created_at: string }[];
  period_days: number;
  scope?: string;
}
