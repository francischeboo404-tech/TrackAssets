# Goods-Receipts 400 Error - Analysis & Fix Summary

## Problem Statement
The `POST /api/receiving/goods-receipts` endpoint was returning a 400 (BAD REQUEST) error when the frontend tried to create a Goods Receipt Note (GRN). The error message was insufficient to diagnose the root cause.

## Investigation Findings

### Database State
- No Purchase Orders existed in the development database initially
- Test data was created: PO id=1 with status='approved', item id=1

### Backend Analysis
1. **Missing Input Validation**: The `create_grn` function didn't validate required fields or check for empty items array
2. **Poor Error Messages**: When validation failed, error messages didn't indicate which field was invalid
3. **Strict Floating-Point Comparison**: Unit cost validation used exact equality, which fails due to floating-point arithmetic issues
4. **No Type Validation**: Request data wasn't validated for type correctness before use

### Environment Issues
- Backend was running with PostgreSQL (production) instead of SQLite (development)
- Different user databases between SQLite dev and PostgreSQL environments
- Authentication failures due to user not existing in the active database

## Fixes Implemented

### 1. Enhanced `ReceivingService.create_grn()` - backend/app/services/receiving_service.py

**Added Validation:**
```python
# Validate input
if not po_id:
    raise ValidationError("po_id is required")
if not items_data or len(items_data) == 0:
    raise ValidationError("At least one item must be provided")
if not received_by_id:
    raise ValidationError("received_by_id is required")
```

**Improved Item Validation:**
- Each item is validated with its index for easier debugging
- Required fields: item_id, quantity_received, unit_cost
- Type conversion with explicit error handling
- Unit cost now uses 0.01 KES tolerance instead of exact matching

**Enhanced Error Messages:**
- "Item 0: quantity_received is required" (vs vague "validation failed")
- "Item 0: Unit cost (2500.5) does not match PO unit cost (2500.0)" (specific values)
- All errors include context about what went wrong

### 2. Improved `_create_grn()` in receiving.py - backend/app/blueprints/receiving.py

**Added Error Handling:**
```python
try:
    grn = ReceivingService.create_grn(...)
    return jsonify({...}), 201
except (ValidationError, NotFoundError) as e:
    raise  # Let error handler format the response
except Exception as e:
    return jsonify({...}), 500
```

**Added Request Validation:**
- Check for null request body before accessing data
- Return clear 400 error if request body is missing

## API Contract

### Request Format (POST /api/receiving/goods-receipts)
```javascript
{
  "po_id": number,              // required
  "items": [                     // required, at least 1 item
    {
      "item_id": number,         // required
      "quantity_received": number, // required, > 0
      "unit_cost": number,       // required, must match PO
      "expiry_date": "YYYY-MM-DD" // optional
    }
  ],
  "invoice_number": string,     // optional
  "delivery_note_number": string // optional
}
```

### Response Formats

**Success (201):**
```json
{
  "message": "GRN created",
  "grn_id": 1,
  "grn_number": "GRN-2026-00001"
}
```

**Validation Error (400):**
```json
{
  "success": false,
  "message": "Item 0: quantity_received is required",
  "errors": [],
  "error": "ValidationError",
  "status_code": 400
}
```

**Not Found (404):**
```json
{
  "success": false,
  "message": "PO not found",
  "errors": [],
  "error": "NotFoundError",
  "status_code": 404
}
```

## Validation Rules Enforced

1. **PO Validation:**
   - PO must exist in the organization
   - PO must have status = 'approved' (not pending, rejected, etc.)
   - PO must have at least one item

2. **Item Validation (per item):**
   - item_id must be part of the PO
   - quantity_received must be > 0
   - quantity_received must not exceed remaining quantity (accounting for previous GRNs)
   - unit_cost must match PO unit cost (±0.01 KES tolerance)
   - All required fields must be present

3. **Authorization:**
   - User must have role: procurement_officer, store_manager, or admin

## Test Data Created

```
Organization: Test Org (id=1)
User: admin@test.com (role=admin)
Supplier: Test Supplier (id=1)
Inventory Item: Office Paper A4 (id=1, SKU=PAPER-A4, unit_price=2500.00)
Purchase Request: PR-2026-00001 (id=1)
  - Item: PAPER-A4, qty=100, estimated_cost=250000.00
Purchase Order: PO-2026-00001 (id=1, status=approved)
  - Item: PAPER-A4, qty=100, unit_cost=2500.00, total_cost=250000.00
```

### Test GRN Creation Request
```json
{
  "po_id": 1,
  "items": [
    {
      "item_id": 1,
      "quantity_received": 50,
      "unit_cost": 2500.00,
      "expiry_date": "2027-01-01"
    }
  ],
  "invoice_number": "INV-2026-001",
  "delivery_note_number": "DN-2026-001"
}
```

## Frontend Changes Recommended

In `useReceiving.ts`, ensure the payload includes all required fields:

```typescript
const payload = {
  po_id: selectedPOId,
  items: selectedItems.map(item => ({
    item_id: item.item_id,
    quantity_received: item.quantityReceived,
    unit_cost: item.unitCost,  // Must match PO
    expiry_date: item.expiryDate || undefined
  })),
  invoice_number: invoiceNumber || undefined,
  delivery_note_number: deliveryNoteNumber || undefined
};
```

## Architecture Notes

### Supply Chain Module Consistency
The Receiving module now follows the same patterns as Procurement:
- **Service Layer**: Validates business logic, raises APIError subclasses
- **Blueprint**: Handles HTTP concerns, auth, error re-raising
- **Error Handling**: ValidationError (400), NotFoundError (404), ConflictError (409)
- **Audit Logging**: All actions logged via AuditService
- **Database**: Uses SQLAlchemy ORM with proper transaction handling

### Related Endpoints
- `POST /api/procurement/purchase-orders/<id>/approve` - Approve PO (status→'approved')
- `GET /api/procurement/purchase-orders/<id>` - Get PO details with items
- `POST /api/receiving/goods-receipts` - Create GRN (this fix)
- `GET /api/receiving/goods-receipts` - List GRNs
- `GET /api/receiving/goods-receipts/<id>` - Get GRN details
- `POST /api/receiving/inspection-reports` - Perform inspection after receiving

## Next Steps

1. **Test GRN Creation**: Verify the fixed endpoint works with test data
2. **Frontend Integration**: Ensure frontend passes all required fields
3. **End-to-End Testing**: Test full workflow: PR → PO → Approve → GRN → Inspection
4. **Supply Chain Architecture Review**: Audit all modules (Procurement, Receiving, Inventory, Transfers) for consistency
5. **Error Handling Audit**: Verify all endpoints return proper error codes

## Files Modified

1. `backend/app/services/receiving_service.py` - Enhanced validation in `create_grn`
2. `backend/app/blueprints/receiving.py` - Improved error handling in `_create_grn`
