# TrackIT RBAC Architecture

## Role mapping (spec → codebase)

| Spec role | Codebase role | Notes |
|-----------|---------------|-------|
| Admin | `admin`, `superadmin` | Full access; superadmin is platform-level |
| Procurement Officer | `dept_head` | Approve/reject assets, transfer approvals |
| Logistics Manager | `staff` | Assign/use/maintenance, stock movements |
| Inventory Manager | `store_manager` | Inventory CRUD (not delete), warehouses |
| Viewer | `viewer` | Read-only |
| (compliance) | `auditor` | Audit logs & reports, read-only mutations |

## Security layers

1. **Frontend** (`frontend/src/lib/permissions.ts`, `Can`, route guards) — UX only
2. **Flask** (`backend/app/auth_utils.py`, `backend/app/rbac.py`, `@require_permission`) — primary enforcement
3. **Supabase RLS** (`supabase/migrations/001_rls_policies.sql`) — org isolation + block direct client writes

## Permission matrix (mutations)

| Action | admin | dept_head | staff | store_manager | viewer | auditor |
|--------|:-----:|:---------:|:-----:|:-------------:|:------:|:-------:|
| Create asset | ✓ | | ✓ | ✓ | | |
| Edit asset metadata | ✓ | | ✓ | ✓ | | |
| Approve/reject asset | ✓ | ✓ | | | | |
| Assign / in use / maintenance | ✓ | | ✓ | ✓ | | |
| Dispose asset | ✓ | | | | | |
| Create inventory | ✓ | | | ✓ | | |
| Edit inventory | ✓ | | | ✓ | | |
| Stock IN/OUT | ✓ | | ✓ | ✓ | | |
| Delete inventory | ✓ | | | | | |
| View analytics (full) | ✓ | scoped | scoped | ✓ | limited | compliance |
| Audit logs | ✓ | | | | | ✓ |

## Asset lifecycle transitions

```
requested → approved | rejected
rejected → requested
approved → in_use
in_use → maintenance | disposed (admin only)
maintenance → in_use | disposed (admin only)
disposed → (terminal)
```

Enforced in `Asset.can_transition_to()` and `rbac.assert_can_transition_status()`.

## Audit logging

All mutations should call `AuditService.log_action()` / `log_asset_change()` / `log_inventory_change()`.

`details` JSON includes: `role`, `previous_state` / `old_values`, `new_state` / `new_values`.

Audit API is append-only at DB policy level; no UPDATE/DELETE on `audit_logs` for clients.

## Previously vulnerable endpoints (fixed)

| Endpoint | Issue | Fix |
|----------|-------|-----|
| `PUT /api/assets/<id>` | Any JWT role could update | `@require_permission("assets:edit")` |
| `PUT /api/assets/<id>/status` | Weak role checks | `rbac.assert_can_transition_status` |
| `PUT /api/inventory/<id>` | `staff` had full edit | `inventory:edit` → store_manager + admin |
| `GET /api/analytics/dashboard/summary` | Full data for all roles | `filter_analytics_payload()` |
| `POST /api/tracking/scan` | viewer could mutate | `assert_not_read_only` |

## Production checklist

- [ ] Apply `supabase/migrations/001_rls_policies.sql` in Supabase SQL editor
- [ ] Confirm backend uses service role / direct Postgres (not anon key for writes)
- [ ] Run `pytest backend/tests/test_rbac.py`
- [ ] Smoke-test each role: login → attempt forbidden action → expect 403
- [ ] Verify audit rows include `role` in `details`
