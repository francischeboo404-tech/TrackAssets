# Reporting & Analytics Architecture

## Overview

TrackIT uses a **server-side aggregation** model: all KPIs, chart series, and percentages are computed in Flask (`ReportAnalyticsService`) via SQLAlchemy `GROUP BY` / `COUNT` / `SUM`. The React UI (Recharts) only renders API payloads — no client-side totals.

## API Endpoints

| Route | Purpose | Roles |
|-------|---------|-------|
| `GET /api/reports/dashboard` | Unified KPIs + nested module summaries | admin, store_manager, auditor, dept_head, staff, viewer (scoped) |
| `GET /api/reports/assets` | Asset status, department, lifecycle, utilization | all except inventory-only roles |
| `GET /api/reports/inventory` | Stock, movements, consumption | not viewer |
| `GET /api/reports/tracking` | Scans, audit-by-role, timelines | not viewer |

Query: `?days=7|30|90` (default 30).

### Response envelope

```json
{
  "success": true,
  "data": { ... },
  "message": "Report generated successfully"
}
```

File exports remain on `/api/reports/asset-register`, `inventory-register`, etc. (PDF/XLSX/CSV).

## Backend modules

- `backend/app/services/report_analytics_service.py` — SQL aggregations + 60s in-process cache per org/report/days
- `backend/app/services/analytics_service.py` — legacy dashboard helpers (reused for valuation, compliance, movement trends)
- `backend/app/rbac.py` — `assert_can_access_report`, `filter_report_payload`

## Frontend

- `frontend/src/hooks/useReportAnalytics.ts` — React Query, 30–60s refetch
- `frontend/src/pages/Analytics.tsx` — tabbed BI dashboard (Overview / Assets / Inventory / Tracking)
- `frontend/src/components/reports/ReportChartPanels.tsx` — Recharts pie, bar, line, timeline list

## Data consistency

- Dashboard `kpis.total_assets` uses the same asset count query as `/reports/assets`.
- `total_valuation` = inventory valuation + asset book value (both from `AnalyticsService`).
- Department heads: assets/dashboard filtered by `User.department` name.

## Supabase

- `supabase/migrations/002_reporting_analytics_indexes.sql` — reporting indexes + `stock_movements` SELECT RLS

## Performance

- 60-second TTL cache on heavy report payloads
- React Query `staleTime` aligned with backend cache
- Pagination not required for chart aggregates (pre-aggregated series)
