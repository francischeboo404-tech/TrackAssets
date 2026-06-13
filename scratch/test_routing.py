from flask import Flask, jsonify
from app import create_app

app = create_app('testing')

with app.test_client() as client:
    # Test inventory creation endpoint
    response = client.post('/api/inventory', json={
        "name": "Test Item",
        "sku": "TEST-SKU",
        "reorder_level": 10,
        "unit_price": 100.0,
        "unit": "pcs"
    })
    print(f"Status Code: {response.status_code}")
    print(f"Data: {response.get_data(as_text=True)}")

    response2 = client.post('/api/inventory/', json={
        "name": "Test Item 2",
        "sku": "TEST-SKU-2",
        "reorder_level": 10,
        "unit_price": 100.0,
        "unit": "pcs"
    })
    print(f"Status Code 2: {response2.status_code}")
    print(f"Data 2: {response2.get_data(as_text=True)}")
