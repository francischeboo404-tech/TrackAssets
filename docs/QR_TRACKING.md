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
