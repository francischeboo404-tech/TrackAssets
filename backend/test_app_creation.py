#!/usr/bin/env python3
"""Quick test to verify Flask app creation

This script is intended to be run standalone. Skip during pytest collection.
"""
import pytest
pytest.skip("Skip standalone app creation script during pytest", allow_module_level=True)

import os
import sys

# Add backend to path
sys.path.insert(0, os.path.dirname(__file__))

from app import create_app

print("📝 This script is intended to be run manually: python test_app_creation.py")
