#!/usr/bin/env python3
"""Check which database config is being used"""
import sys
import os
os.chdir('c:\\Users\\fivid\\Desktop\\Nova Lite Limited\\TrackIT-main\\backend')
sys.path.insert(0, 'c:\\Users\\fivid\\Desktop\\Nova Lite Limited\\TrackIT-main\\backend')

from app import create_app

app = create_app('development')
print(f"Current config: {app.config.get('ENV', 'N/A')}")
print(f"Database URI: {app.config['SQLALCHEMY_DATABASE_URI']}")
