#!/usr/bin/env python3
"""Quick test to verify Flask app creation"""

import os
import sys

# Add backend to path
sys.path.insert(0, os.path.dirname(__file__))

try:
    from app import create_app
    
    print("📝 Testing app creation...")
    app = create_app('development')
    print("✅ App created successfully in development mode!")
    
    print("\n📝 Testing app creation in production mode...")
    app_prod = create_app('production')
    print("✅ App created successfully in production mode!")
    
    print("\n✅ All tests passed! Flask app is working correctly.")
    
except Exception as e:
    print(f"❌ Error: {type(e).__name__}: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
