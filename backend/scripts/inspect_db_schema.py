import sqlite3
from pathlib import Path

db_path = Path(__file__).resolve().parents[1] / 'trackit_dev.db'
print('DB path:', db_path)
conn = sqlite3.connect(str(db_path))
cur = conn.cursor()

# alembic_version
try:
    cur.execute('SELECT version_num FROM alembic_version')
    versions = cur.fetchall()
    print('alembic_version rows:', versions)
except Exception as e:
    print('alembic_version query failed:', e)

# audit_logs columns
try:
    cur.execute("PRAGMA table_info('audit_logs')")
    cols = cur.fetchall()
    print('audit_logs columns:')
    for c in cols:
        print(' ', c)
except Exception as e:
    print('audit_logs pragma failed:', e)

conn.close()
