# Warehouse Hierarchy REST API - Curl Examples

## Setup

### 1. Get Bearer Token
```bash
curl -X POST http://localhost:5000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "email": "admin@example.com",
    "password": "password123"
  }'

# Save the token from response
export TOKEN="your-jwt-token-here"
export ORG_ID=1
```

---

## Warehouse Hierarchy Management

### 1. Get Main Warehouse
```bash
curl -X GET http://localhost:5000/api/warehouses/hierarchy/main \
  -H "Authorization: Bearer $TOKEN" \
  -H "X-Organization-ID: $ORG_ID"
```

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
  "child_warehouses": [
    {"id": 6, "name": "Branch 1", "code": "B1-001"},
    {"id": 7, "name": "Branch 2", "code": "B2-002"}
  ]
}
```

### 2. Get Complete Hierarchy Tree
```bash
curl -X GET http://localhost:5000/api/warehouses/hierarchy/structure \
  -H "Authorization: Bearer $TOKEN" \
  -H "X-Organization-ID: $ORG_ID"
```

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
      },
      {
        "id": 7,
        "name": "Branch 2",
        "code": "B2-002",
        "hierarchy_level": 1,
        "children": []
      }
    ]
  }
}
```

### 3. Get Warehouse Hierarchy Info
```bash
curl -X GET http://localhost:5000/api/warehouses/5/hierarchy-info \
  -H "Authorization: Bearer $TOKEN" \
  -H "X-Organization-ID: $ORG_ID"
```

**Response:**
```json
{
  "id": 5,
  "name": "Central Warehouse",
  "code": "CW-001",
  "is_main": true,
  "warehouse_type": "main",
  "hierarchy_level": 0,
  "parent_warehouse_id": null,
  "parent_warehouse": null,
  "child_warehouse_count": 2,
  "child_warehouses": [
    {"id": 6, "name": "Branch 1", "code": "B1-001"},
    {"id": 7, "name": "Branch 2", "code": "B2-002"}
  ],
  "ancestors": []
}
```

### 4. Set Main Warehouse (ADMIN ONLY)
```bash
curl -X PATCH http://localhost:5000/api/warehouses/5/set-main \
  -H "Authorization: Bearer $TOKEN" \
  -H "X-Organization-ID: $ORG_ID" \
  -H "Content-Type: application/json" \
  -d '{
    "reason": "Designated as primary distribution center"
  }'
```

**Response:**
```json
{
  "message": "Warehouse set as main warehouse",
  "warehouse": {
    "id": 5,
    "name": "Central Warehouse",
    "code": "CW-001",
    "is_main": true,
    "warehouse_type": "main",
    "hierarchy_level": 0
  },
  "previous_main_warehouse": null
}
```

### 5. Add Child Warehouse (ADMIN ONLY)
```bash
curl -X PATCH http://localhost:5000/api/warehouses/6/set-parent/5 \
  -H "Authorization: Bearer $TOKEN" \
  -H "X-Organization-ID: $ORG_ID" \
  -H "Content-Type: application/json" \
  -d '{
    "reason": "Adding branch as child of main warehouse"
  }'
```

**Response:**
```json
{
  "message": "Parent-child relationship created",
  "warehouse": {
    "id": 6,
    "name": "Branch 1",
    "code": "B1-001",
    "parent_warehouse_id": 5,
    "warehouse_type": "storage_facility",
    "hierarchy_level": 1
  }
}
```

### 6. Move Warehouse in Hierarchy (ADMIN ONLY)
```bash
curl -X PATCH http://localhost:5000/api/warehouses/6/move-to/7 \
  -H "Authorization: Bearer $TOKEN" \
  -H "X-Organization-ID: $ORG_ID" \
  -H "Content-Type: application/json" \
  -d '{
    "reason": "Reorganizing warehouse structure"
  }'
```

**Response:**
```json
{
  "message": "Warehouse moved successfully",
  "warehouse": {
    "id": 6,
    "name": "Branch 1",
    "code": "B1-001",
    "parent_warehouse_id": 7,
    "hierarchy_level": 2
  }
}
```

---

## Inventory Transfers

### 1. Transfer from Main to Branch
```bash
curl -X POST http://localhost:5000/api/transfers/inventory/hierarchy-transfer \
  -H "Authorization: Bearer $TOKEN" \
  -H "X-Organization-ID: $ORG_ID" \
  -H "Content-Type: application/json" \
  -d '{
    "inventory_item_id": 123,
    "quantity": 50,
    "from_warehouse_id": 5,
    "to_warehouse_id": 6,
    "notes": "Monthly distribution to Branch 1"
  }'
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

### 2. Transfer from Branch to Main
```bash
curl -X POST http://localhost:5000/api/transfers/inventory/hierarchy-transfer \
  -H "Authorization: Bearer $TOKEN" \
  -H "X-Organization-ID: $ORG_ID" \
  -H "Content-Type: application/json" \
  -d '{
    "inventory_item_id": 123,
    "quantity": 30,
    "from_warehouse_id": 6,
    "to_warehouse_id": 5,
    "notes": "Return of excess stock"
  }'
```

### 3. Invalid Transfer (Branch to Branch)
```bash
curl -X POST http://localhost:5000/api/transfers/inventory/hierarchy-transfer \
  -H "Authorization: Bearer $TOKEN" \
  -H "X-Organization-ID: $ORG_ID" \
  -H "Content-Type: application/json" \
  -d '{
    "inventory_item_id": 123,
    "quantity": 25,
    "from_warehouse_id": 6,
    "to_warehouse_id": 7,
    "notes": "Transfer to sibling branch"
  }'
```

**Response (Error):**
```json
{
  "error": "Direct transfer between child warehouses is not allowed. Items must be transferred through the main warehouse.",
  "status_code": 409
}
```

### 4. Insufficient Stock Transfer
```bash
curl -X POST http://localhost:5000/api/transfers/inventory/hierarchy-transfer \
  -H "Authorization: Bearer $TOKEN" \
  -H "X-Organization-ID: $ORG_ID" \
  -H "Content-Type: application/json" \
  -d '{
    "inventory_item_id": 123,
    "quantity": 1000,
    "from_warehouse_id": 5,
    "to_warehouse_id": 6,
    "notes": "Requesting more than available"
  }'
```

**Response (Error):**
```json
{
  "error": "Insufficient stock in source warehouse. Available: 200, Requested: 1000",
  "status_code": 400
}
```

---

## Error Responses

### 401 Unauthorized (Missing/Invalid Token)
```json
{
  "error": "Missing or invalid authorization token",
  "status_code": 401
}
```

### 403 Forbidden (Insufficient Permissions)
```json
{
  "error": "You do not have permission to perform this action",
  "status_code": 403
}
```

### 404 Not Found
```json
{
  "error": "Warehouse not found",
  "status_code": 404
}
```

### 409 Conflict (Invalid Transfer Path)
```json
{
  "error": "Direct transfer between child warehouses is not allowed. Items must be transferred through the main warehouse.",
  "status_code": 409
}
```

### 429 Too Many Requests (Rate Limited)
```json
{
  "error": "Rate limit exceeded. Maximum 50 requests per minute.",
  "status_code": 429
}
```

---

## Response Headers

All responses include:
```
Content-Type: application/json
X-Organization-ID: 1
X-Request-ID: uuid-here
Cache-Control: no-cache
```

---

## Testing Workflow

### Step 1: Login
```bash
TOKEN=$(curl -s -X POST http://localhost:5000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"admin@example.com","password":"password"}' \
  | jq -r '.access_token')

echo "Token: $TOKEN"
```

### Step 2: Get Initial Hierarchy
```bash
curl -s -X GET http://localhost:5000/api/warehouses/hierarchy/structure \
  -H "Authorization: Bearer $TOKEN" \
  -H "X-Organization-ID: 1" | jq .
```

### Step 3: Set Main Warehouse
```bash
curl -s -X PATCH http://localhost:5000/api/warehouses/5/set-main \
  -H "Authorization: Bearer $TOKEN" \
  -H "X-Organization-ID: 1" \
  -H "Content-Type: application/json" \
  -d '{}' | jq .
```

### Step 4: Add Child Warehouses
```bash
curl -s -X PATCH http://localhost:5000/api/warehouses/6/set-parent/5 \
  -H "Authorization: Bearer $TOKEN" \
  -H "X-Organization-ID: 1" \
  -H "Content-Type: application/json" \
  -d '{}' | jq .

curl -s -X PATCH http://localhost:5000/api/warehouses/7/set-parent/5 \
  -H "Authorization: Bearer $TOKEN" \
  -H "X-Organization-ID: 1" \
  -H "Content-Type: application/json" \
  -d '{}' | jq .
```

### Step 5: Verify Hierarchy
```bash
curl -s -X GET http://localhost:5000/api/warehouses/hierarchy/structure \
  -H "Authorization: Bearer $TOKEN" \
  -H "X-Organization-ID: 1" | jq .
```

### Step 6: Transfer Inventory
```bash
curl -s -X POST http://localhost:5000/api/transfers/inventory/hierarchy-transfer \
  -H "Authorization: Bearer $TOKEN" \
  -H "X-Organization-ID: 1" \
  -H "Content-Type: application/json" \
  -d '{
    "inventory_item_id": 123,
    "quantity": 50,
    "from_warehouse_id": 5,
    "to_warehouse_id": 6,
    "notes": "Test transfer"
  }' | jq .
```

### Step 7: Test Invalid Transfer (Should Fail)
```bash
curl -s -X POST http://localhost:5000/api/transfers/inventory/hierarchy-transfer \
  -H "Authorization: Bearer $TOKEN" \
  -H "X-Organization-ID: 1" \
  -H "Content-Type: application/json" \
  -d '{
    "inventory_item_id": 123,
    "quantity": 25,
    "from_warehouse_id": 6,
    "to_warehouse_id": 7,
    "notes": "Invalid sibling transfer"
  }' | jq .
```

---

## Postman Collection

Import this collection into Postman for easier testing:

```json
{
  "info": {
    "name": "Warehouse Hierarchy API",
    "version": "1.0.0"
  },
  "item": [
    {
      "name": "Get Main Warehouse",
      "request": {
        "method": "GET",
        "url": "{{base_url}}/api/warehouses/hierarchy/main",
        "header": [
          {"key": "Authorization", "value": "Bearer {{token}}"},
          {"key": "X-Organization-ID", "value": "{{org_id}}"}
        ]
      }
    },
    {
      "name": "Get Hierarchy Structure",
      "request": {
        "method": "GET",
        "url": "{{base_url}}/api/warehouses/hierarchy/structure",
        "header": [
          {"key": "Authorization", "value": "Bearer {{token}}"},
          {"key": "X-Organization-ID", "value": "{{org_id}}"}
        ]
      }
    },
    {
      "name": "Transfer Inventory",
      "request": {
        "method": "POST",
        "url": "{{base_url}}/api/transfers/inventory/hierarchy-transfer",
        "header": [
          {"key": "Authorization", "value": "Bearer {{token}}"},
          {"key": "X-Organization-ID", "value": "{{org_id}}"},
          {"key": "Content-Type", "value": "application/json"}
        ],
        "body": {
          "mode": "raw",
          "raw": "{\"inventory_item_id\": 123, \"quantity\": 50, \"from_warehouse_id\": 5, \"to_warehouse_id\": 6, \"notes\": \"Test\"}"
        }
      }
    }
  ]
}
```

---

## Environment Variables (Postman)

```json
{
  "base_url": "http://localhost:5000",
  "org_id": "1",
  "token": "your-jwt-token",
  "main_warehouse_id": "5",
  "branch_warehouse_id": "6",
  "inventory_item_id": "123"
}
```
