# System Settings — Architecture & Status

## Components

| Layer | Path | Role |
|-------|------|------|
| API | `backend/app/blueprints/settings.py` | REST endpoints |
| Service | `backend/app/services/settings_service.py` | Validation, export, purge, logo |
| Model | `backend/app/models/organization.py` | `preferences` JSON, `logo_url` |
| UI | `frontend/src/pages/Settings.tsx` | 4 tabs: General, Security, Notifications, Data |
| Hooks | `frontend/src/hooks/useSettings.ts` | React Query mutations |
| Static | `/static/uploads/logos/<file>` | Logo delivery |

## Endpoints (admin only)

| Method | Path | Function |
|--------|------|----------|
| GET | `/api/settings/organization` | Load org profile + preferences |
| PUT | `/api/settings/organization` | Update name + whitelisted preferences |
| POST | `/api/settings/organization/logo` | Upload logo (≤2MB) |
| POST | `/api/settings/organization/export` | CSV export |
| DELETE | `/api/settings/organization/purge` | Delete stock movements &gt;3 years |

## Preference keys (persisted)

| Key | Active in app |
|-----|----------------|
| `currency` | Yes — dashboard, analytics, reports |
| `critical_alerts` | Stored; restock system uses thresholds |
| `daily_digest` | Stored — email job not implemented |
| `strict_password` | Stored — baseline 8-char policy always enforced on `User.set_password` |
| `require_2fa` | Stored — enforcement planned |
| `session_timeout` | Stored — JWT expiry fixed in config today |

## Real-time

`ORGANIZATION_UPDATE` SSE event invalidates `['settings', 'organization']` cache.

## Tests

`backend/tests/test_settings.py` — export fields, preference whitelist, admin RBAC.
