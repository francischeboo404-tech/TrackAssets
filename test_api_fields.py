#!/usr/bin/env python
"""Test script to verify API returns new inventory master data fields"""

import requests
import json

def test_inventory_fields():
    print("=" * 60)
    print("Testing Inventory API - New Master Data Fields")
    print("=" * 60)
    
    # Step 1: Login
    print("\n1. Logging in...")
    login_resp = requests.post('http://localhost:5000/api/auth/login', json={
        'email': 'admin@techcorp.com',
        'password': 'Admin123!'
    }, timeout=10)
    
    if login_resp.status_code != 200:
        print(f"   ❌ Login failed: {login_resp.status_code}")
        print(f"   {login_resp.text}")
        return
    
    token = login_resp.json().get('access_token')
    print(f"   ✓ Login successful, token: {token[:20]}...")
    
    # Step 2: Get inventory items
    print("\n2. Fetching inventory items...")
    inv_resp = requests.get('http://localhost:5000/api/inventory', headers={
        'Authorization': f'Bearer {token}'
    }, timeout=10)
    
    if inv_resp.status_code != 200:
        print(f"   ❌ GET /api/inventory failed: {inv_resp.status_code}")
        print(f"   {inv_resp.text}")
        return
    
    data = inv_resp.json()
    items = data.get('inventory', [])
    print(f"   ✓ Retrieved {len(items)} inventory items")
    
    if not items:
        print("   ⚠ No inventory items found in database")
        return
    
    # Step 3: Check new fields
    print("\n3. Verifying new master data fields in response...")
    item = items[0]
    
    new_fields = [
        'category_id', 'item_type', 'status', 'preferred_supplier_id',
        'supplier_item_reference', 'purchase_cost', 'last_purchase_cost',
        'tax_category', 'lead_time_days', 'min_stock_level', 'max_stock_level',
        'safety_stock', 'opening_stock', 'batch_tracking', 'serial_tracking', 'expiry_tracking'
    ]
    
    print(f"\n   Sample Item: ID={item.get('id')}, Name={item.get('name')}, SKU={item.get('sku')}")
    print(f"\n   Checking {len(new_fields)} new fields:")
    
    present_count = 0
    missing_count = 0
    
    for field in new_fields:
        if field in item:
            value = item[field]
            status = "✓"
            present_count += 1
        else:
            value = "MISSING"
            status = "❌"
            missing_count += 1
        
        print(f"   {status} {field}: {value}")
    
    print(f"\n   Summary: {present_count} fields present, {missing_count} fields missing")
    
    # Step 4: Test batch endpoints
    print("\n4. Testing batch endpoints...")
    batch_resp = requests.get('http://localhost:5000/api/inventory/batches', headers={
        'Authorization': f'Bearer {token}'
    }, timeout=10)
    
    print(f"   GET /api/inventory/batches: {batch_resp.status_code}")
    if batch_resp.status_code == 200:
        batch_data = batch_resp.json()
        batches = batch_data.get('batches', [])
        print(f"   ✓ Retrieved {len(batches)} batches")
        if batches:
            print(f"   Sample batch fields: {list(batches[0].keys())}")
    else:
        print(f"   ❌ Error: {batch_resp.text[:200]}")
    
    # Step 5: Summary
    print("\n" + "=" * 60)
    print("Test Complete")
    print("=" * 60)

if __name__ == '__main__':
    test_inventory_fields()
