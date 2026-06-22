# Transfer Asset — Implementation Guide

## Overview

This document describes the implementation plan for the Transfer Asset feature in the TrackIT Asset Management Module. The feature introduces three transfer types — **Employee to Employee**, **Department to Department**, and **Warehouse to Warehouse** — each following the same approval workflow that already exists for department transfers.

The existing `TransferRequest` model, service, and blueprint are extended rather than replaced. The core approval lifecycle (pending → approved → in_transit → completed) is preserved for all three types.

---

## Transfer Types

| Type | What changes on the asset | When it applies |
|---|---|---|
| Employee to Employee | `assigned_to_user_id`, `assigned_to`, `assignment_date` | Asset is currently `assigned` to someone |
| Department to Department | `department_id`, `location` | Asset in any non-disposed status |
| Warehouse to Warehouse | `warehouse_id`, `bin_id` | Asset stored in a warehouse |

---

## Data Stored per Transfer

For every transfer request (all three types), the system records:

| Field | Description |
|---|---|
| Previous owner | Captured automatically at request time from the asset's current state |
| New owner | Supplied in the request payload |
| Transfer date | `requested_at` (when the request was made), `reviewed_at` (when completed) |
| Reason | Free-text `comment` field on the transfer request |
| Transfer type | `transfer_type` column on `TransferRequest` |

---

## Approval Lifecycle

All three transfer types share the same four-step flow:

```
pending → approved → in_transit → completed
```

- **pending**: Request submitted; awaiting manager review.
- **approved**: A manager or admin approved the request.
- **in_transit**: Asset has been dispatched/is in transit. The asset's `location` field is updated to reflect the move in progress.
- **completed** (receive): Transfer finalised. The asset's relevant fields are updated based on transfer type.

---

## Backend Changes

### 1. TransferRequest Model

**File:** `backend/app/models/transfer.py`

Four new columns are added:

- `transfer_type` — categorises the transfer; defaults to `department_to_department` for backwards compatibility with existing rows.
- `from_user_id` — FK to `users.id`; the user who previously held the asset (captured automatically at request time for employee transfers).
- `to_user_id` — FK to `users.id`; the user who will receive the asset.
- `from_warehouse_id` — FK to `warehouses.id`; the source warehouse (captured automatically for warehouse transfers).

Two new relationships are added: `from_user` and `to_user`.

**Note on existing NOT NULL columns:** `from_department_id` and `to_department_id` remain NOT NULL. For non-department transfers, both are set to the asset's current `department_id` (no department change occurs).

---

### 2. Database Migration

**File:** New file in `backend/migrations/versions/`

- Adds the four new columns to the `transfer_requests` table.
- Data migration sets `transfer_type = 'department_to_department'` for all existing rows.
- No existing columns are modified or made nullable.

---

### 3. Validation Schema

**File:** `backend/app/validation.py` — update `TransferRequestSchema`

- `transfer_type` field added (required).
- `to_user_id` field added (optional integer).
- A cross-field validator enforces that the correct field is present for each type:
  - `employee_to_employee` — requires `to_user_id`
  - `department_to_department` — requires `new_department_id`
  - `warehouse_to_warehouse` — requires `to_warehouse_id`

---

### 4. Repository

**File:** `backend/app/repositories/transfer_repository.py`

`create_request(...)` is updated to accept and persist `transfer_type`, `from_user_id`, `to_user_id`, and `from_warehouse_id`.

---

### 5. Transfer Service

**File:** `backend/app/services/transfer_service.py`

#### `request_transfer`

Extended to accept `transfer_type`, `to_user_id`, `to_warehouse_id`, and `to_bin_id`.

From-state is captured automatically:
- Employee transfer: reads `asset.assigned_to_user_id` into `from_user_id`. Validates that the asset is currently `assigned`.
- Warehouse transfer: reads `asset.warehouse_id` into `from_warehouse_id`.
- Department transfer: unchanged; reads `asset.department_id`.

For all types, `from_department_id` and `to_department_id` are always populated (same value for non-dept transfers).

#### `dispatch_request`

Sets `asset.location` with a type-appropriate message:
- Employee: "Transfer in progress to {to_user first name}"
- Warehouse: "In Transit to {to_warehouse name}"
- Department: existing "In Transit to {to_department name}" (unchanged)

#### `receive_request`

Branches on `transfer_type` to determine what gets updated:
- **Employee to Employee**: updates `asset.assigned_to_user_id`, `asset.assigned_to`, and `asset.assignment_date`. Asset status remains `assigned`.
- **Department to Department**: existing logic unchanged — updates `asset.department_id` and `asset.location`.
- **Warehouse to Warehouse**: updates `asset.warehouse_id` and `asset.bin_id` (if provided); updates bin statuses.

Audit log for all completions includes `transfer_type`, previous owner, new owner, and reason.

---

### 6. Transfer Blueprint

**File:** `backend/app/blueprints/transfers.py`

The `POST /transfers/` handler is updated to extract `transfer_type` and `to_user_id` from the validated request body and pass them through to `transfer_service.request_transfer(...)`.

Approve, reject, dispatch, and receive endpoints require no changes — the service handles all branching.

---

## Frontend Changes

### 7. TransferAssetModal (new component)

**File:** `frontend/src/components/ui/TransferAssetModal.tsx`

A modal following the same pattern as `AssignAssetModal.tsx` and `ReturnAssetModal.tsx`.

**Form structure:**

1. **Transfer type selection** — radio or segmented control:
   - Employee to Employee
   - Department to Department
   - Warehouse to Warehouse

2. **Type-specific fields** rendered conditionally:
   - *Employee*: dropdown to select the destination user (active users, current assignee excluded). Only enabled when the asset status is `assigned`.
   - *Department*: dropdown to select the destination department.
   - *Warehouse*: dropdown to select the destination warehouse; optional secondary dropdown for a specific bin (loads after warehouse is chosen).

3. **Reason field** — text area (required) — maps to `comment`.

On submit, calls `POST /transfers/` with the appropriate payload.

---

### 8. Mutation Hook

**File:** `frontend/src/hooks/useAssets.ts` (or `useTransfers.ts`)

A new `useRequestTransfer()` mutation hook is added, posting to `POST /transfers/` with the transfer payload. On success it invalidates the `assets`, `asset`, and `transfers` React Query caches.

---

### 9. Assets Page

**File:** `frontend/src/pages/Assets.tsx`

- New state variable: `selectedAssetForTransfer`
- "Transfer" action button added to each asset row. Visible for `store_manager` and `admin` roles when `asset.status !== 'disposed'`.
- `<TransferAssetModal>` rendered and wired to the new state.

---

## Audit Trail

Every transfer request action is logged to `audit_logs`. The `details` JSON on each log entry includes:

- `transfer_type`
- `from_owner` — user ID or warehouse ID depending on type
- `to_owner` — the new owner
- `reason` — the comment provided at request time
- `transfer_request_id`

---

## Verification Steps

1. Run `flask db upgrade` to apply the migration.
2. Open an `assigned` asset → click Transfer → select *Employee to Employee* → pick a different active user → provide a reason → submit.
3. Confirm the request appears in the transfers list as `pending`.
4. Approve → Dispatch → Receive the request.
5. Verify `asset.assigned_to_user_id` reflects the new user and the audit log contains `ASSET_TRANSFER` with the correct before/after owner.
6. Repeat the same flow for *Department to Department* (confirm `asset.department_id` changes) and *Warehouse to Warehouse* (confirm `asset.warehouse_id` changes).
7. Confirm that `comment` is stored on the `TransferRequest` and appears in the audit log `details.reason`.
8. Confirm that transferring a `disposed` asset is blocked.
