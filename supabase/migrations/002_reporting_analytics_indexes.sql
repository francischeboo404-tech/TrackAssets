-- Reporting & analytics performance indexes (Supabase / PostgreSQL)
-- Complements Flask-SQLAlchemy indexes; safe to run on managed Postgres.

CREATE INDEX IF NOT EXISTS ix_assets_org_status_reporting
  ON assets (organisation_id, status);

CREATE INDEX IF NOT EXISTS ix_assets_org_dept_reporting
  ON assets (organisation_id, department_id);

CREATE INDEX IF NOT EXISTS ix_inventory_items_org_active_qty
  ON inventory_items (organisation_id, is_active, quantity);

CREATE INDEX IF NOT EXISTS ix_stock_movements_item_date
  ON stock_movements (item_id, date DESC);

CREATE INDEX IF NOT EXISTS ix_scan_events_org_ts_reporting
  ON scan_events (organisation_id, timestamp DESC);

CREATE INDEX IF NOT EXISTS ix_audit_logs_org_created_reporting
  ON audit_logs (organisation_id, created_at DESC);

CREATE INDEX IF NOT EXISTS ix_audit_logs_org_action_entity
  ON audit_logs (organisation_id, action, entity_type);

-- RLS: allow org-scoped SELECT for analytics (service role / JWT org claim)
-- stock_movements were missing policies in 001 — read-only for same org
DO $$
BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM pg_policies
    WHERE tablename = 'stock_movements' AND policyname = 'stock_movements_org_select'
  ) THEN
    CREATE POLICY stock_movements_org_select ON stock_movements
      FOR SELECT
      USING (organisation_id = current_org_id());
  END IF;
EXCEPTION
  WHEN undefined_function THEN
    NULL; -- current_org_id() exists only after 001_rls_policies.sql
END $$;
