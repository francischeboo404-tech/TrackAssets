# Misplaced Items Detection — Implementation Guide

**Status:** Feature stub (incomplete)  
**Last Updated:** 2026-07-11  
**Target:** Replace empty `predict_misplaced_items()` stub in `backend/app/services/anomaly_service.py`

---

## Overview

The misplaced items detection feature identifies inventory and assets whose **recorded physical location** (warehouse/bin from the latest scan) does not match their **expected location** (the department they belong to or are assigned to).

### Example Scenarios
- An asset assigned to Department A is found in Department B's warehouse
- An inventory item stored in Warehouse East but should be in Warehouse Main
- A laptop marked as assigned to Employee X but scanned in Building Y's storage bin
- An item that has not been scanned recently (stale location data)

---

## Key Concepts

### Item Types
TrackIT tracks two primary item types:

1. **Assets** (`asset`)
   - Fixed, durable equipment (laptops, furniture, machinery)
   - Has an `assigned_department_id` (where it's assigned) or `assigned_to_user_id` (personal assignment)
   - Current location tracked via `warehouse_id` and `bin_id` (from latest scan)
   - Status: available, assigned, under_maintenance, lost, damaged, disposed

2. **Inventory Instances** (`inventory_instance`)
   - Individual tracked units of consumable inventory
   - Has an expected `warehouse_id` (primary storage location)
   - Current location from latest scan may differ

### Location Hierarchy
```
Organization
└── Warehouse (e.g., "Main Storage")
    └── WarehouseZone (e.g., "Zone A")
        └── WarehouseRack (e.g., "Rack 1")
            └── WarehouseShelf (e.g., "Shelf 3")
                └── WarehouseBin (e.g., "Bin 5")
                    └── Item (asset, inventory_instance)
```

### Tracking Data
- **ScanEvent**: Immutable record of every QR scan; contains `item_type`, `item_id`, `warehouse_id`, `bin_id`, `timestamp`, and GPS coordinates
- **Latest Location**: The most recent ScanEvent for an item determines its current location
- **Expected Location**: Stored on the Asset/InventoryItem model itself

---

## Files to Read First

An intern implementing this feature must understand:

### 1. **Domain Models** (read in order)
- `backend/app/models/asset.py` (lines 34–96)
  - Asset model structure
  - `department_id` (home department), `assigned_department_id` (current assignment)
  - `assigned_to_user_id` (personal assignment)
  - `warehouse_id`, `bin_id` (current physical location)
  
- `backend/app/models/inventory.py` (lines 15–78)
  - InventoryItem model; focus on `warehouse_id` (expected location)
  
- `backend/app/models/item_instance.py`
  - ItemInstance model (individual serialized units)
  - `warehouse_id`, `bin_id`, status field
  
- `backend/app/models/scan_event.py`
  - ScanEvent structure; critical fields: `item_type`, `item_id`, `warehouse_id`, `bin_id`, `timestamp`, `validation_status`
  - Indexes: composite on `(item_type, item_id)` and `(organisation_id, timestamp)`

### 2. **Current Anomaly Detection** (understand existing patterns)
- `backend/app/services/anomaly_service.py` (entire file)
  - Study `analyze_scan()` for impossible travel detection (warehouse change in < 10 min)
  - Study `detect_duplicate_scans()` for multi-device logic
  - Note: `predict_misplaced_items()` is the stub you're implementing (line 79–83)

### 3. **Tracking Service Integration** (where anomalies are used)
- `backend/app/services/tracking_service.py`
  - Search for `analyze_scan()` call (~line 180–185)
  - See how anomalies are returned in the API response
  - Understand how location updates are applied (`_apply_scan_effects()`)

### 4. **API Response Contract** (frontend expectations)
- `backend/app/blueprints/tracking.py` (lines ~120–180)
  - `POST /api/tracking/scan` endpoint
  - Response includes `anomalies` field (currently used for impossible travel)
  
- `frontend/src/hooks/useTracking.ts`
  - Study `useRecordScan()` mutation
  - See how scan response is consumed

### 5. **Frontend Integration** (optional, understand constraints)
- `frontend/src/pages/Tracking.tsx` (lines ~200–250)
  - Where scan response is handled
  - Currently ignores anomalies in response
  
- `frontend/src/services/trackingService.ts`
  - API call wrapper for `/api/tracking/scan`

### 6. **Tests** (understand patterns)
- `backend/tests/test_tracking_ai.py`
  - Full scan lifecycle test
  - Shows how to create items, scan them, and verify state

### 7. **Database Layout** (context only)
- `backend/migrations/` — Alembic migration files
  - Shows database schema evolution
  - Helpful to understand indexes and constraints

---

## Implementation Phases

### Phase 1: Understand the Data (Design)
**Goal:** Map the logical relationships between items, locations, and expected locations.

**Tasks:**
1. Diagram the relationship:
   - Asset → assigned_department_id (expected) vs. warehouse_id (actual)
   - Asset → assigned_to_user_id → User → Department (expected) vs. warehouse_id (actual)
   - InventoryItem → warehouse_id (expected) vs. latest ScanEvent.warehouse_id (actual)
   - ItemInstance → warehouse_id (expected) vs. latest ScanEvent.warehouse_id (actual)

2. Define "misplaced":
   - For assets: current scan location differs from assigned department's expected warehouse
   - For inventory: current scan location differs from item's declared warehouse_id
   - Time consideration: Is an item stale if last scanned > 30 days ago?
   - Grace period: Items in transit (TRANSFER action) have a grace period?

3. Document edge cases:
   - Assets with no assignment yet (status = available)
   - Items in maintenance (status = under_maintenance)
   - Disposed/lost items (should not be flagged as misplaced)
   - Items with no scans (no location data yet)

**Deliverable:** Design doc or comment block in the code explaining decision logic.

---

### Phase 2: Database Query Design (Backend)
**Goal:** Write efficient SQL/ORM queries to fetch misplaced items.

**Key Decisions:**
1. **How to find latest scan per item:**
   - Subquery: `SELECT DISTINCT ON (item_type, item_id) ... ORDER BY timestamp DESC`
   - Window function: `ROW_NUMBER() OVER (PARTITION BY item_type, item_id ORDER BY timestamp DESC)`
   - Multiple joins: For each item type separately
   
2. **How to define expected location:**
   - For assets: Join to `Department` → get its `warehouse_id`; or use `assigned_department_id` → Department → warehouse_id
   - For inventory: Use `warehouse_id` field directly
   - For item instances: Use `warehouse_id` field directly

3. **Performance considerations:**
   - Use existing indexes on `(organisation_id, timestamp)` and `(item_type, item_id)`
   - Avoid N+1 queries; use `joinedload()` or explicit joins
   - Consider pagination for large datasets (100K+ items)

**Tangible Artifacts:**
- SQLAlchemy ORM queries (NOT raw SQL)
- Explain each join/filter in code comments
- Mock test queries with sample data

---

### Phase 3: Anomaly Detection Logic (Backend)
**Goal:** Implement `predict_misplaced_items(org_id)` method in `AnomalyService`.

**Requirements:**
1. **Input:** `org_id` (organisation ID)
2. **Output:** List of dictionaries, each containing:
   ```
   {
     "type": "MISPLACED_ITEM",
     "severity": "MEDIUM" | "HIGH",
     "item_type": "asset" | "inventory_instance",
     "item_id": <int>,
     "item_name": <str>,
     "expected_location": {"warehouse_id": <int>, "warehouse_name": <str>},
     "actual_location": {"warehouse_id": <int>, "warehouse_name": <str>, "bin_id": <int>, "timestamp": <datetime>},
     "days_since_scan": <int>,
     "message": <str>
   }
   ```

3. **Logic:**
   - For each asset and inventory item in the org:
     - Find latest scan (if any)
     - Compare scan location to expected location
     - If mismatch, add to anomalies list
   - Sort by severity and days since scan (oldest first)

4. **Severity Scoring:**
   - HIGH: Item found in completely different warehouse
   - MEDIUM: Item found in same warehouse but different zone/rack/bin
   - LOW: Stale location (no scan in 30+ days)

**Edge Cases to Handle:**
- Item never scanned (no ScanEvent) → flag as severity HIGH with note "No scan history"
- Item in transit (last action = TRANSFER) → skip or flag as severity LOW with note "In transit"
- Disposed/lost item (status = disposed/lost) → skip
- Item assigned to user without a department → handle gracefully

---

### Phase 4: Integration with Scan Flow (Backend)
**Goal:** Call `predict_misplaced_items()` and include results in API responses.

**Requirements:**
1. **Where to call:**
   - `tracking_service.py` → `record_scan()` method, after `analyze_scan()` call
   - OR: Create a new broader anomaly method that calls both

2. **When to call:**
   - After every scan? (expensive, runs for every org item)
   - On-demand only? (dashboard, analytics page)
   - Background job? (requires async infrastructure; not available in TrackIT)
   - Scheduled batch? (cron job; needs setup)

   **Recommendation for Phase 4:** Call on-demand only via a new endpoint `/api/tracking/misplaced-items`. Full scan integration deferred to Phase 5.

3. **API Response:**
   - Add `misplaced_items: [...]` field to existing scan response
   - OR: Create new endpoint `GET /api/tracking/misplaced-items?org_id=X&limit=50`

---

### Phase 5: Frontend Display (Frontend)
**Goal:** Show misplaced items to the user in real-time.

**Requirements:**
1. **Where to display:**
   - Tracking page: Add a "Misplaced Items" alert banner if any detected
   - New analytics/dashboard card: "Inventory Health" showing count of misplaced items
   - Scan result modal: Display misplaced items anomaly inline with impossible travel

2. **Interaction:**
   - Click to view item details
   - Filter by severity
   - Acknowledge / mark as reviewed
   - Link to location history (trace where it moved)

3. **Real-Time Updates:**
   - Via SSE: Publish `MISPLACED_ITEM_DETECTED` event when scan reveals a misplaced item
   - Update counts on LiveTrackingContext
   - Toast notification for high-severity misplacements

---

### Phase 6: Testing (Throughout)
**Goal:** Ensure correctness and performance.

**Test Cases:**
1. **Unit Tests** (`test_anomaly_service.py`):
   - Create assets/items with expected locations
   - Create scans at different locations
   - Call `predict_misplaced_items()` → verify detection
   - Edge cases: no scans, disposed items, in-transit items

2. **Integration Tests** (`test_tracking_ai.py`):
   - Full flow: Create warehouse, asset, scan it in wrong location
   - Verify scan response includes anomaly
   - Verify frontend hook receives and renders it

3. **Performance Tests:**
   - 1000 items with scans → query time should be < 2s
   - Test database indexes are being used (EXPLAIN QUERY PLAN)

---

## Architectural Decisions

### Decision 1: On-Demand vs. Batch Processing
**Option A (Chosen for Phase 4):** On-demand via new endpoint
- **Pros:** Low latency for small datasets, easy to implement, no async infra needed
- **Cons:** Expensive for large orgs (100K+ items), cannot be called per-scan
- **Action:** Implement Phase 4 with on-demand endpoint

**Option B:** Batch processing (after async infra added)
- **Pros:** Efficient, can be scheduled nightly, suitable for 100K+ items
- **Cons:** Requires Celery or similar; not available in current TrackIT
- **Action:** Document for future enhancement

---

### Decision 2: Severity Scoring
**Chosen Approach:** 3-level severity (HIGH, MEDIUM, LOW)
- HIGH: Wrong warehouse entirely
- MEDIUM: Same warehouse, different zone/bin
- LOW: Stale data (> 30 days since scan)

**Rationale:** Allows prioritization in UI; ops can focus on highest-risk misplacements first.

---

### Decision 3: Expected Location Resolution
**Chosen Approach:** Multi-level lookup

For assets:
1. If `assigned_to_user_id` is set → get User → get Department → warehouse_id
2. Else if `assigned_department_id` is set → get Department → warehouse_id
3. Else use `department_id` → get Department → warehouse_id

For inventory:
- Use `warehouse_id` field directly

**Rationale:** Assets can have complex assignments (personal or departmental); need to resolve all paths.

---

### Decision 4: Stale Data Threshold
**Chosen Approach:** 30 days without a scan = severity LOW

**Rationale:** Inventory practices vary; 30 days is a reasonable "aged" threshold without being too strict. Configurable via env var.

---

## Integration Checklist

Before marking the feature complete:

- [ ] **Database**: No new tables or migrations required (uses existing ScanEvent, Asset, InventoryItem)
- [ ] **Backend Service**: `predict_misplaced_items()` implemented and tested
- [ ] **API**: New endpoint (or updated existing) returns anomalies
- [ ] **Frontend Hook**: `useRecordScan()` or new `useMisplacedItems()` consumes API
- [ ] **Frontend UI**: Misplaced items displayed with severity coloring
- [ ] **SSE Events**: Optional — MISPLACED_ITEM_DETECTED event published (Phase 5+)
- [ ] **Tests**: Unit + integration tests passing
- [ ] **Documentation**: Code comments explain logic, edge cases documented
- [ ] **Performance**: Query time < 2s for typical org sizes

---

## Questions for Clarification

Before starting implementation, get answers to:

1. **Scope:** Should this detect misplaced items for all item types (assets + inventory + instances) or just assets?
2. **Frequency:** On-demand only, or should every scan also check for misplaced items?
3. **Grace Period:** Should items in TRANSFER action be excluded from misplaced detection?
4. **Stale Threshold:** 30 days without a scan — agree, or different?
5. **UI Location:** Tracking page, separate analytics card, or both?
6. **Severity Levels:** 3 levels (HIGH/MEDIUM/LOW) — agree, or different?
7. **Expected Location:** For assets assigned to users, use their department's warehouse or a separate personal location?

---

## Success Criteria

The feature is complete when:

1. ✅ No items are incorrectly flagged as misplaced
2. ✅ All actually misplaced items are detected
3. ✅ Severity scoring matches business intent
4. ✅ API response includes clear, actionable anomaly details
5. ✅ Frontend displays anomalies prominently
6. ✅ Tests pass (unit + integration)
7. ✅ Query performance is acceptable (< 2s)
8. ✅ Edge cases handled (disposed items, no-scan items, in-transit items)

---

## References

- **Live Tracking Plan**: `docs/` (other feature docs in this directory)
- **Anomaly Service**: `backend/app/services/anomaly_service.py`
- **Tracking Service**: `backend/app/services/tracking_service.py`
- **Models**: `backend/app/models/{asset,inventory,scan_event}.py`
- **Tests**: `backend/tests/test_tracking_ai.py`, `test_anomaly_service.py`
