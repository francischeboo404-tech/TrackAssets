#!/usr/bin/env python3
"""Get default test user password"""
import sys
import os
os.chdir('c:\\Users\\fivid\\Desktop\\Nova Lite Limited\\TrackIT-main\\backend')
sys.path.insert(0, 'c:\\Users\\fivid\\Desktop\\Nova Lite Limited\\TrackIT-main\\backend')

from app import create_app, db
from app.models.user import User

app = create_app('development')

with app.app_context():
    user = User.query.filter_by(email='admin@test.com').first()
    if user:
        print(f"User: {user.email}, Role: {user.role}")
        # Try setting a known password
        user.set_password('Admin@123456')
        db.session.commit()
        print("Password set to: Admin@123456")
