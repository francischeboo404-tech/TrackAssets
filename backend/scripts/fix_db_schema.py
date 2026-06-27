import sqlite3
from pathlib import Path

db_path = Path(__file__).resolve().parents[1] / 'trackit_dev.db'
print('DB path:', db_path)
conn = sqlite3.connect(str(db_path))
cur = conn.cursor()

# helper
def has_column(table, column):
    cur.execute(f"PRAGMA table_info('{table}')")
    cols = [c[1] for c in cur.fetchall()]
    return column in cols

# add user_agent and reference if missing
try:
    if not has_column('audit_logs', 'user_agent'):
        print('Adding column user_agent to audit_logs')
        cur.execute("ALTER TABLE audit_logs ADD COLUMN user_agent VARCHAR(255)")
    else:
        print('user_agent already present')
    if not has_column('audit_logs', 'reference'):
        print('Adding column reference to audit_logs')
        cur.execute("ALTER TABLE audit_logs ADD COLUMN reference VARCHAR(255)")
    else:
        print('reference already present')
    if not has_column('audit_logs', 'module'):
        print('Adding column module to audit_logs')
        cur.execute("ALTER TABLE audit_logs ADD COLUMN module VARCHAR(100)")
    else:
        print('module already present')

    # create indexes if not present (sqlite has no IF NOT EXISTS for CREATE INDEX until 3.8.0, but we'll catch exceptions)
    try:
        cur.execute("CREATE INDEX ix_audit_logs_user_agent ON audit_logs(user_agent)")
    except Exception as e:
        print('ix_audit_logs_user_agent create skipped:', e)
    try:
        cur.execute("CREATE INDEX ix_audit_logs_reference ON audit_logs(reference)")
    except Exception as e:
        print('ix_audit_logs_reference create skipped:', e)
    try:
        cur.execute("CREATE INDEX ix_audit_logs_module ON audit_logs(module)")
    except Exception as e:
        print('ix_audit_logs_module create skipped:', e)

    conn.commit()
    print('Schema fix applied')
except Exception as e:
    print('Schema fix failed:', e)
finally:
    conn.close()
