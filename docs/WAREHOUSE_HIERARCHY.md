# Hierarchical Warehouse Management System

## Overview

The TrackIT system now implements a **hierarchical warehouse structure** similar to SAP ERP systems, where:

- **Main Warehouse**: Acts as the parent/central facility for inventory distribution
- **Storage Facilities**: Act as child warehouses under the main warehouse
- **Stock Transfers**: Flow through the warehouse hierarchy with enforced business rules

This architecture ensures proper inventory management across multiple locations while maintaining audit trails and preventing unauthorized transfers.

---

## Architecture

### Database Schema

#### Warehouse Model Enhancements

Added hierarchy-related columns to the `warehouses` table:

```sql
ALTER TABLE warehouses ADD COLUMN parent_warehouse_id INTEGER;
ALTER TABLE warehouses ADD COLUMN is_main_warehouse BOOLEAN DEFAULT FALSE;
ALTER TABLE warehouses ADD COLUMN warehouse_type VARCHAR(50) DEFAULT 'storage_facility';
ALTER TABLE warehouses ADD COLUMN hierarchy_level INTEGER DEFAULT 0;

-- Foreign key for parent-child relationship
ALTER TABLE warehouses ADD FOREIGN KEY (parent_warehouse_id) REFERENCES warehouses(id) ON DELETE SET NULL;

-- Indexes for performance
CREATE INDEX ix_warehouses_parent_id ON warehouses(parent_warehouse_id);
CREATE INDEX ix_warehouses_is_main ON warehouses(is_main_warehouse);
CREATE INDEX ix_warehouses_warehouse_type ON warehouses(warehouse_type);
```

**Fields:**
- `parent_warehouse_id`: References another warehouse (NULL for main warehouse)
- `is_main_warehouse`: Boolean flag indicating this is the main warehouse (ONE per organization)
- `warehouse_type`: Either 'main' or 'storage_facility'
- `hierarchy_level`: Depth in hierarchy (0 = main, 1+ = children)

---

## Core Services

### 1. WarehouseHierarchyService

**Location**: `app/services/warehouse_hierarchy_service.py`

Manages all warehouse hierarchy operations with built-in validation.

#### Key Methods

##### `get_main_warehouse(org_id: int) -> Warehouse`
Retrieves the main warehouse for an organization.

```python
from app.services.warehouse_hierarchy_service import WarehouseHierarchyService

main_warehouse = WarehouseHierarchyService.get_main_warehouse(org_id=1)
```

##### `set_main_warehouse(warehouse_id: int, org_id: int) -> Warehouse`
Sets a warehouse as the main warehouse (demotes any existing main warehouse).

```python
main_warehouse = WarehouseHierarchyService.set_main_warehouse(
    warehouse_id=5, 
    org_id=1
)
# Result: warehouse_type='main', is_main_warehouse=True, hierarchy_level=0
```

##### `add_child_warehouse(child_warehouse_id, parent_warehouse_id, org_id)`
Adds a warehouse as a child of another warehouse.

```python
child = WarehouseHierarchyService.add_child_warehouse(
    child_warehouse_id=6,      # Storage facility
    parent_warehouse_id=5,     # Main warehouse
    org_id=1
)
# Result: parent_warehouse_id=5, warehouse_type='storage_facility', hierarchy_level=1
```

##### `get_warehouse_hierarchy(org_id: int) -> dict`
Returns the complete warehouse hierarchy as a nested dictionary.

```python
hierarchy = WarehouseHierarchyService.get_warehouse_hierarchy(org_id=1)

# Output:
# {
#   "id": 5,
#   "name": "Main Warehouse",
#   "code": "MW-001",
#   "is_main": true,
#   "hierarchy_level": 0,
#   "children": [
#     {
#       "id": 6,
#       "name": "Branch Warehouse 1",
#       "code": "BW-001",
#       "hierarchy_level": 1,
#       "children": []
#     },
#     {
#       "id": 7,
#       "name": "Branch Warehouse 2",
#       "code": "BW-002",
#       "hierarchy_level": 1,
#       "children": []
#     }
#   ]
# }
```

##### `validate_transfer_path(from_warehouse_id, to_warehouse_id, org_id) -> bool`
Validates that a transfer is allowed by warehouse hierarchy rules.

**Transfer Rules (SAP-like):**
- ✅ Main warehouse can transfer to ANY child warehouse
- ✅ Child can transfer to parent (main warehouse)
- ✅ Child can transfer to main warehouse directly
- ❌ Child CANNOT transfer directly to another child (must go through main)

```python
# Valid: Main → Child
WarehouseHierarchyService.validate_transfer_path(
    from_warehouse_id=5,  # Main
    to_warehouse_id=6,    # Child
    org_id=1
)  # Returns: True

# Valid: Child → Main
WarehouseHierarchyService.validate_transfer_path(
    from_warehouse_id=6,  # Child
    to_warehouse_id=5,    # Main
    org_id=1
)  # Returns: True

# Invalid: Child → Child (raises ConflictError)
WarehouseHierarchyService.validate_transfer_path(
    from_warehouse_id=6,  # Child 1
    to_warehouse_id=7,    # Child 2
    org_id=1
)  # Raises: ConflictError
```

---

### 2. StockService Enhancement

**Location**: `app/services/stock_service.py`

Added `transfer_with_hierarchy()` method for warehouse-to-warehouse transfers.

#### Method Signature

```python
def transfer_with_hierarchy(
    self,
    item_id: int,
    org_id: int,
    quantity: int,
    from_warehouse_id: int,
    to_warehouse_id: int,
    user_id: int = None,
    reference: str = None,
    notes: str = None,
    commit: bool = True
) -> dict
```

#### Functionality

1. **Validates warehouse hierarchy relationship** - Ensures transfer is allowed
2. **Decreases stock at source warehouse** - Reduces `quantity_on_hand`
3. **Increases stock at destination warehouse** - Creates warehouse stock if needed
4. **Creates audit trail** - Logs action with warehouse details and user info
5. **Updates stock cards and ledgers** - Maintains StockCard and SuppliesLedgerCard
6. **Publishes event** - Triggers `STOCK_TRANSFERRED` event for async listeners

#### Usage Example

```python
from app.services.stock_service import StockService

stock_service = StockService()

result = stock_service.transfer_with_hierarchy(
    item_id=123,
    org_id=1,
    quantity=50,
    from_warehouse_id=5,      # Main warehouse
    to_warehouse_id=6,        # Branch warehouse
    user_id=42,
    notes="Monthly distribution to branch",
    commit=True
)

# Result:
# {
#   "item_id": 123,
#   "from_warehouse_id": 5,
#   "to_warehouse_id": 6,
#   "quantity": 50,
#   "status": "transferred"
# }
```

#### Audit Trail

Each transfer creates a detailed audit entry:

```python
{
    "action": "STOCK_TRANSFERRED_BETWEEN_WAREHOUSES",
    "entity_id": 123,  # item_id
    "details": {
        "item_name": "Medical Supplies Box",
        "item_sku": "MED-001",
        "quantity": 50,
        "from_warehouse_id": 5,
        "from_warehouse_name": "Main Warehouse",
        "from_previous_quantity": 150,
        "from_new_quantity": 100,
        "to_warehouse_id": 6,
        "to_warehouse_name": "Branch Warehouse 1",
        "to_previous_quantity": 0,
        "to_new_quantity": 50,
        "reference": "MON-DIST-001",
        "notes": "Monthly distribution to branch"
    }
}
```

---

## REST API Endpoints

### Warehouse Hierarchy Management

#### Get Main Warehouse
```
GET /api/warehouses/hierarchy/main
```
Returns the main warehouse for the organization.

**Response:**
```json
{
  "id": 5,
  "name": "Central Warehouse",
  "code": "CW-001",
  "address": "123 Main Street",
  "is_main": true,
  "warehouse_type": "main",
  "hierarchy_level": 0,
  "parent_warehouse_id": null,
  "parent_warehouse": null,
  "child_warehouses": [
    {"id": 6, "name": "Branch 1", "code": "B1-001", "hierarchy_level": 1},
    {"id": 7, "name": "Branch 2", "code": "B2-002", "hierarchy_level": 1}
  ]
}
```

#### Get Complete Hierarchy
```
GET /api/warehouses/hierarchy/structure
```
Returns the complete warehouse hierarchy tree.

**Response:**
```json
{
  "hierarchy": {
    "id": 5,
    "name": "Central Warehouse",
    "code": "CW-001",
    "is_main": true,
    "hierarchy_level": 0,
    "children": [
      {
        "id": 6,
        "name": "Branch 1",
        "code": "B1-001",
        "hierarchy_level": 1,
        "children": []
      }
    ]
  }
}
```

#### Set Main Warehouse (Admin Only)
```
PATCH /api/warehouses/<warehouse_id>/set-main
```
Sets a warehouse as the main warehouse for the organization.

**Permission**: Admin role required

#### Set Warehouse Parent (Admin Only)
```
PATCH /api/warehouses/<child_warehouse_id>/set-parent/<parent_warehouse_id>
```
Adds a warehouse as a child of another warehouse.

#### Move Warehouse in Hierarchy (Admin Only)
```
PATCH /api/warehouses/<warehouse_id>/move-to/<new_parent_warehouse_id>
```
Moves a warehouse to a different parent.

#### Get Warehouse Hierarchy Info
```
GET /api/warehouses/<warehouse_id>/hierarchy-info
```
Gets hierarchy information for a specific warehouse.

---

### Inventory Transfer Endpoints

#### Hierarchy-Aware Transfer (New!)
```
POST /api/transfers/inventory/hierarchy-transfer
```
Transfers inventory items between warehouses with hierarchy validation.

**Permission**: Admin, Staff, or Store Manager

**Rate Limit**: 50 per minute

**Request Body:**
```json
{
  "inventory_item_id": 123,
  "quantity": 50,
  "from_warehouse_id": 5,
  "to_warehouse_id": 6,
  "notes": "Monthly distribution"
}
```

**Response (Success):**
```json
{
  "message": "Inventory transferred successfully",
  "transfer": {
    "item_id": 123,
    "from_warehouse_id": 5,
    "to_warehouse_id": 6,
    "quantity": 50,
    "status": "transferred"
  }
}
```

**Response (Hierarchy Violation):**
```json
{
  "error": "Direct transfer between child warehouses is not allowed. Items must be transferred through the main warehouse."
}
```
Status: 409 Conflict

**Response (Insufficient Stock):**
```json
{
  "error": "Insufficient stock in source warehouse. Available: 30, Requested: 50"
}
```
Status: 400 Bad Request

---

## Workflow Examples

### Scenario 1: Monthly Distribution to Branch

**Objective**: Distribute items from main warehouse to multiple branches

```python
# 1. Get main warehouse
main_wh = WarehouseHierarchyService.get_main_warehouse(org_id=1)
print(f"Main warehouse: {main_wh.name} ({main_wh.id})")

# 2. Get all branches (child warehouses)
branches = main_wh.child_warehouses
for branch in branches:
    print(f"  - {branch.name} ({branch.id})")

# 3. Transfer specific items to each branch
stock_service = StockService()
for branch in branches:
    stock_service.transfer_with_hierarchy(
        item_id=MEDICAL_SUPPLY_ITEM_ID,
        org_id=1,
        quantity=50,
        from_warehouse_id=main_wh.id,
        to_warehouse_id=branch.id,
        notes=f"Monthly distribution to {branch.name}",
        commit=True
    )
    print(f"✓ Transferred 50 units to {branch.name}")
```

### Scenario 2: Return Inventory from Branch to Main

```python
# Branch manager returns excess inventory to main warehouse
stock_service = StockService()
result = stock_service.transfer_with_hierarchy(
    item_id=MEDICAL_SUPPLY_ITEM_ID,
    org_id=1,
    quantity=30,
    from_warehouse_id=6,  # Branch warehouse
    to_warehouse_id=5,    # Main warehouse
    user_id=branch_manager_user_id,
    notes="Return of excess stock - expiry approaching",
    commit=True
)
print(f"✓ Returned {result['quantity']} units to main warehouse")
```

### Scenario 3: Consolidation Before Main Transfer

```python
# Consolidate inventory from multiple branches before main transfer out

# Step 1: Check if transfer between branches is attempted (should fail)
try:
    WarehouseHierarchyService.validate_transfer_path(
        from_warehouse_id=6,  # Branch 1
        to_warehouse_id=7,    # Branch 2
        org_id=1
    )
except ConflictError as e:
    print(f"❌ Cannot transfer directly: {e}")
    print("✓ Routing through main warehouse instead...")

# Step 2: Transfer Branch 1 → Main
stock_service.transfer_with_hierarchy(
    item_id=ITEM_ID,
    org_id=1,
    quantity=25,
    from_warehouse_id=6,   # Branch 1
    to_warehouse_id=5,     # Main
    notes="Return from branch 1",
    commit=True
)

# Step 3: Transfer Branch 2 → Main
stock_service.transfer_with_hierarchy(
    item_id=ITEM_ID,
    org_id=1,
    quantity=20,
    from_warehouse_id=7,   # Branch 2
    to_warehouse_id=5,     # Main
    notes="Return from branch 2",
    commit=True
)

print("✓ Consolidated to main warehouse")
```

---

## Error Handling

### Common Errors

#### 1. ConflictError: Direct Child-to-Child Transfer

```python
# ❌ This will raise ConflictError
try:
    stock_service.transfer_with_hierarchy(
        item_id=123,
        org_id=1,
        quantity=50,
        from_warehouse_id=6,  # Child 1
        to_warehouse_id=7,    # Child 2 (sibling)
        commit=True
    )
except ConflictError as e:
    print(f"Error: {e}")
    # Output: "Direct transfer between child warehouses is not allowed..."
```

#### 2. ValueError: Insufficient Stock

```python
# ❌ This will raise ValueError
try:
    stock_service.transfer_with_hierarchy(
        item_id=123,
        org_id=1,
        quantity=100,  # More than available
        from_warehouse_id=5,
        to_warehouse_id=6,
        commit=True
    )
except ValueError as e:
    print(f"Error: {e}")
    # Output: "Insufficient stock in source warehouse. Available: 50, Requested: 100"
```

#### 3. NotFoundError: Warehouse Not Found

```python
# ❌ This will raise NotFoundError
try:
    WarehouseHierarchyService.get_main_warehouse(org_id=999)
except NotFoundError as e:
    print(f"Error: {e}")
    # Output: "No main warehouse configured for this organization..."
```

---

## Testing

### Running Tests

```bash
# Run all warehouse hierarchy tests
pytest tests/test_warehouse_hierarchy.py -v

# Run specific test class
pytest tests/test_warehouse_hierarchy.py::TestWarehouseHierarchy -v

# Run specific test
pytest tests/test_warehouse_hierarchy.py::TestWarehouseHierarchy::test_set_main_warehouse -v
```

### Test Coverage

- ✅ Setting main warehouse
- ✅ Getting main warehouse
- ✅ Adding child warehouses
- ✅ Retrieving hierarchy structure
- ✅ Validating main-to-child transfers
- ✅ Validating child-to-main transfers
- ✅ Blocking child-to-child transfers
- ✅ Executing transfers with stock updates
- ✅ Handling insufficient stock errors

**Result**: 9/9 tests PASSING ✅

---

## Security & Access Control

### Role-Based Access Control (RBAC)

| Endpoint | Role Required | Permission |
|----------|---------------|-----------|
| GET /hierarchy/main | Any authenticated | View main warehouse |
| GET /hierarchy/structure | Any authenticated | View hierarchy |
| PATCH /set-main | Admin | Configure main warehouse |
| PATCH /set-parent | Admin | Configure hierarchy |
| PATCH /move-to | Admin | Modify hierarchy |
| POST /inventory/hierarchy-transfer | Admin, Staff, Store Manager | Perform transfers |

### Audit Trail

Every warehouse transfer is logged with:
- User ID (who performed the transfer)
- Timestamp
- Source warehouse details
- Destination warehouse details
- Previous and new stock levels
- Reference and notes

---

## Frontend Integration

### Display Warehouse Hierarchy

**TypeScript/React Component:**

```typescript
import { useEffect, useState } from 'react';

interface Warehouse {
  id: number;
  name: string;
  code: string;
  hierarchy_level: number;
  is_main: boolean;
  children: Warehouse[];
}

export function WarehouseHierarchy() {
  const [hierarchy, setHierarchy] = useState<Warehouse | null>(null);

  useEffect(() => {
    fetch('/api/warehouses/hierarchy/structure')
      .then(res => res.json())
      .then(data => setHierarchy(data.hierarchy));
  }, []);

  const renderNode = (warehouse: Warehouse, level: number) => (
    <div key={warehouse.id} style={{ marginLeft: `${level * 20}px` }}>
      <div className="warehouse-node">
        <strong>{warehouse.name}</strong> ({warehouse.code})
        {warehouse.is_main && <span className="badge">Main</span>}
      </div>
      {warehouse.children && warehouse.children.map(child => 
        renderNode(child, level + 1)
      )}
    </div>
  );

  return hierarchy ? renderNode(hierarchy, 0) : <div>Loading...</div>;
}
```

### Transfer Interface

```typescript
async function performTransfer(
  itemId: number,
  quantity: number,
  fromWarehouseId: number,
  toWarehouseId: number,
  notes?: string
) {
  try {
    const response = await fetch('/api/transfers/inventory/hierarchy-transfer', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        inventory_item_id: itemId,
        quantity,
        from_warehouse_id: fromWarehouseId,
        to_warehouse_id: toWarehouseId,
        notes
      })
    });

    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.error);
    }

    const result = await response.json();
    console.log(`✓ Transferred ${result.transfer.quantity} units`);
    return result;
  } catch (error) {
    console.error(`Transfer failed: ${error.message}`);
    throw error;
  }
}
```

---

## SAP ERP Compatibility

This implementation follows SAP's Multi-Warehouse Inventory Management principles:

| Feature | SAP | TrackIT |
|---------|-----|---------|
| Hierarchical warehouses | ✅ | ✅ |
| Main warehouse concept | ✅ | ✅ |
| Parent-child transfers | ✅ | ✅ |
| Stock authorization levels | ✅ | ✅ (via RBAC) |
| Audit trail for transfers | ✅ | ✅ |
| Warehouse consolidation | ✅ | ✅ |
| Transfer blocking rules | ✅ | ✅ |

---

## Migration Notes

### Database Changes Applied

Migration: `add_warehouse_hierarchy.py`

**Changes:**
- Added 4 new columns to `warehouses` table
- Added self-referential foreign key
- Created 3 performance indexes

**Backward Compatibility**: ✅ Fully backward compatible
- Existing warehouses not affected
- Default values ensure legacy functionality
- No data loss

**Rollback**: Supported via Alembic downgrade

---

## Configuration

### System Settings (Future Enhancement)

Settings for warehouse hierarchy management can be configured via:

```python
from app.models import SystemSetting

# Set main warehouse
SystemSetting.set('org_main_warehouse_id', warehouse_id, org_id)

# Get main warehouse
main_warehouse_id = SystemSetting.get('org_main_warehouse_id', org_id)
```

---

## Performance Optimization

### Indexes

Three indexes created for query optimization:
- `ix_warehouses_parent_id` - Fast lookup of child warehouses
- `ix_warehouses_is_main` - Quick identification of main warehouse
- `ix_warehouses_warehouse_type` - Type-based filtering

### Query Efficiency

Hierarchy lookups use recursive CTEs (Common Table Expressions) for efficiency in database queries.

---

## Known Limitations & Future Enhancements

### Current Limitations
1. **One level deep child warehouses** - Only direct parent-child supported (no grandchildren)
2. **No warehouse deactivation cascade** - Deactivating parent doesn't deactivate children

### Planned Enhancements
1. Multi-level hierarchy support (unlimited depth)
2. Automatic warehouse consolidation workflows
3. Transfer forecasting and planning
4. Warehouse capacity management
5. Location-based transfer rules

---

## Support & Troubleshooting

### Common Issues

**Issue**: "No main warehouse configured for this organization"
- **Solution**: Use `WarehouseHierarchyService.set_main_warehouse()` to designate main warehouse

**Issue**: "Direct transfer between child warehouses is not allowed"
- **Solution**: Route transfers through main warehouse (Child → Main → Child)

**Issue**: Transfer succeeds but stock levels not updated
- **Solution**: Verify `commit=True` and check for transaction rollbacks in logs

---

## References

- [Stock Service Documentation](stock_service.md)
- [Inventory Management API](inventory_api.md)
- [Audit System Documentation](audit_system.md)
- [RBAC Documentation](rbac.md)
