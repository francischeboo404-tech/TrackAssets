# QR Real-Time Tracking System

## Secure payload design

Inner payload (before HMAC):

```
v1:{entity_type}:{organisation_id}:{entity_id}:{exp_unix}
```

Signed token: `{inner}:{hmac_sha256_12chars}`

Public scan URL: `{TRACKING_PUBLIC_URL}?data={signed_token}`

Legacy assets also support `asset:{org_id}:{asset_code}` with signature.

## Backend endpoints

| Method | Path | Purpose |
|--------|------|---------|
| GET | `/api/tracking/qr/{entity_type}/{entity_id}` | Generate signed QR |
| POST | `/api/tracking/scan` | Validate + log + apply state |
| POST | `/api/tracking/scan/verify` | Read-only verification |
| GET | `/api/tracking/history/{type}/{id}` | Immutable timeline |
| GET | `/api/tracking/allowed-actions` | Role-permitted scan types |

## Scan event schema (`scan_events`)

- `user_role`, `previous_state`, `new_state` (JSON)
- `validation_status` (`verified` / `duplicate`)
- `scan_fingerprint` (dedup within `SCAN_DEDUP_SECONDS`, default 30s)

## Real-time updates

`TrackingService` publishes `SCAN_EVENT` on the existing SSE bus (`/api/analytics/stream`). Frontend `useSSE` invalidates assets, inventory, and history caches.

Transport details worth knowing:

- `record_scan` buffers its events and publishes them only after the transaction
  commits, so a client never refetches data that has not landed yet.
- `event_bus.publish()` writes on a connection of its own and never commits the
  caller's transaction.
- The stream emits an SSE `id:` per event and a comment heartbeat every ~15s. The
  heartbeat both keeps proxies from cutting an idle connection (nginx and Render
  cut at ~55-60s) and lets the generator notice a client that has gone away.
- A reconnecting client resumes from a cursor, passed as `Last-Event-ID` or, for
  `EventSource` which cannot set headers, as `?last_event_id=`. Without one, a
  cold connect replays the last five seconds.
- `system_events` rows are pruned by a daily cron job; see `BACKEND_SETUP.md`.
- 
## Security

- HMAC verification server-side only (`SECRET_KEY`)
- Expiry enforced (`QR_PAYLOAD_TTL_DAYS`)
- No raw ID-only QR acceptance for new codes
- RBAC via `tracking_rbac.py`
- Supabase RLS: scan_events append-only for clients

## Production checklist

- Set `TRACKING_PUBLIC_URL` to production frontend `/tracking`
- Apply `supabase/migrations/001_rls_policies.sql` scan_events policies
- Run Alembic migration `b2c4e8f1a901`

- Set `VITE_MAP_TILE_URL` and `VITE_MAP_TILE_ATTRIBUTION` to a keyed tile
  provider. The defaults point at the public OpenStreetMap tile servers, which
  their usage policy does not permit for production traffic
- Set `CRON_SECRET` and schedule `/cron/prune-system-events` daily alongside the
  existing `/cron/keepalive` job
- Scrub query strings from access logs for `/api/analytics/stream`, which carries
  the JWT in the URL (see `BACKEND_SETUP.md`)
