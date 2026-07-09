#!/usr/bin/env python3
"""List all users in the database"""
import sys
import os
os.chdir('c:\\Users\\fivid\\Desktop\\Nova Lite Limited\\TrackIT-main\\backend')
sys.path.insert(0, 'c:\\Users\\fivid\\Desktop\\Nova Lite Limited\\TrackIT-main\\backend')

from app import create_app, db
from app.models.user import User

app = create_app('development')

with app.app_context():
    users = User.query.all()
    print(f"Total users: {len(users)}\n")
    for u in users:
        print(f"ID={u.id}, Email={u.email}, Role={u.role}, Org={u.organisation_id}")
