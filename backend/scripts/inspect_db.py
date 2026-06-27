#!/usr/bin/env python3
"""Inspect configured SQLite DB and list tables for troubleshooting."""
import os
import sys
import sqlite3
from pathlib import Path

# Ensure the project backend folder is on sys.path so `import app` works
repo_root = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(repo_root))

from app import create_app

app = create_app('development')
uri = app.config.get('SQLALCHEMY_DATABASE_URI') or ''
print('SQLALCHEMY_DATABASE_URI =', uri)

dbpath = None
if uri.startswith('sqlite:///'):
    dbpath = uri.replace('sqlite:///', '')
elif uri.startswith('sqlite://'):
    dbpath = uri.replace('sqlite://', '')

print('dbpath =', dbpath)
if dbpath:
    abs_path = os.path.abspath(dbpath)
    print('abs path =', abs_path)
    print('exists =', os.path.exists(abs_path))
    try:
        conn = sqlite3.connect(abs_path)
        cur = conn.cursor()
        cur.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name;")
        tables = [r[0] for r in cur.fetchall()]
        print('tables =', tables)
        if 'users' in tables:
            try:
                cur.execute('SELECT COUNT(1) FROM users')
                print('users rowcount =', cur.fetchone()[0])
            except Exception as e:
                print('could not count users rows:', e)
        else:
            print('users table NOT found')
        conn.close()
    except Exception as e:
        print('ERROR inspecting sqlite file:', e)
else:
    print('Not using sqlite (database engine is not sqlite)')


def inspect_alternate_db(path: str):
    """Also inspect backend/app/trackit_dev.db if present (possible alternate file)."""
    try:
        alt = Path(path)
        if not alt.exists():
            print(f"alternate db not found: {alt}")
            return
        print(f"Inspecting alternate DB: {alt}")
        conn = sqlite3.connect(str(alt))
        cur = conn.cursor()
        cur.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name;")
        tables = [r[0] for r in cur.fetchall()]
        print('alt tables =', tables)
        if 'users' in tables:
            try:
                cur.execute('SELECT COUNT(1) FROM users')
                print('alt users rowcount =', cur.fetchone()[0])
            except Exception as e:
                print('could not count alt users rows:', e)
        conn.close()
    except Exception as e:
        print('ERROR inspecting alternate sqlite file:', e)


# Check possible alternate path under backend/app
alternate = repo_root.joinpath('app', 'trackit_dev.db')
if alternate.exists() and str(alternate) != os.path.abspath(dbpath or ''):
    inspect_alternate_db(alternate)
