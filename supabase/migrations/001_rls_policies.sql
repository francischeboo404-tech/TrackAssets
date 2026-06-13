-- TrackIT Row Level Security policies
-- Apply with Supabase SQL editor or migration runner.
-- Backend uses service role / direct Postgres; RLS blocks anon/authenticated client bypass.

ALTER TABLE IF EXISTS users ENABLE ROW LEVEL SECURITY;
ALTER TABLE IF EXISTS assets ENABLE ROW LEVEL SECURITY;
ALTER TABLE IF EXISTS inventory_items ENABLE ROW LEVEL SECURITY;
ALTER TABLE IF EXISTS audit_logs ENABLE ROW LEVEL SECURITY;
ALTER TABLE IF EXISTS stock_movements ENABLE ROW LEVEL SECURITY;
ALTER TABLE IF EXISTS departments ENABLE ROW LEVEL SECURITY;
ALTER TABLE IF EXISTS warehouses ENABLE ROW LEVEL SECURITY;
ALTER TABLE IF EXISTS scan_events ENABLE ROW LEVEL SECURITY;

-- Organisation isolation (JWT claim organisation_id must match row)
CREATE OR REPLACE FUNCTION public.current_org_id() RETURNS integer AS $$
  SELECT NULLIF(current_setting('request.jwt.claims', true)::json->>'organisation_id', '')::integer;
$$ LANGUAGE sql STABLE;

-- SELECT: same organisation only
CREATE POLICY assets_select_org ON assets
  FOR SELECT USING (organisation_id = public.current_org_id());

CREATE POLICY inventory_select_org ON inventory_items
  FOR SELECT USING (organisation_id = public.current_org_id());

CREATE POLICY audit_select_org ON audit_logs
  FOR SELECT USING (organisation_id = public.current_org_id());

CREATE POLICY scan_events_select_org ON scan_events
  FOR SELECT USING (organisation_id = public.current_org_id());

CREATE POLICY scan_events_insert_org ON scan_events
  FOR INSERT WITH CHECK (organisation_id = public.current_org_id());

CREATE POLICY scan_events_no_update ON scan_events
  FOR UPDATE USING (false);
CREATE POLICY scan_events_no_delete ON scan_events
  FOR DELETE USING (false);

-- INSERT/UPDATE/DELETE: deny direct client writes (backend service role only)
CREATE POLICY assets_no_client_write ON assets
  FOR ALL USING (false) WITH CHECK (false);

CREATE POLICY inventory_no_client_write ON inventory_items
  FOR ALL USING (false) WITH CHECK (false);

CREATE POLICY audit_append_only ON audit_logs
  FOR INSERT WITH CHECK (organisation_id = public.current_org_id());

CREATE POLICY audit_no_update_delete ON audit_logs
  FOR UPDATE USING (false);
CREATE POLICY audit_no_delete ON audit_logs
  FOR DELETE USING (false);

-- Users: read own org members only
CREATE POLICY users_select_org ON users
  FOR SELECT USING (organisation_id = public.current_org_id());

CREATE POLICY users_no_client_write ON users
  FOR ALL USING (false) WITH CHECK (false);
