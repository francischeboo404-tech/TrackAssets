import sqlite3
import os

db_path = r"c:\Users\fivid\Desktop\Nova Lite Limited\Assets_Inventory_TrackIT\backend\app\trackit_dev.db"

def check_db():
    if not os.path.exists(db_path):
        print(f"Database not found at {db_path}")
        return

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    print("--- Departments ---")
    cursor.execute("SELECT id, name, code, organisation_id, is_active FROM departments")
    for row in cursor.fetchall():
        print(row)

    print("\n--- Users ---")
    cursor.execute("SELECT id, username, first_name, last_name, organisation_id FROM users")
    for row in cursor.fetchall():
        print(row)

    print("\n--- Assets ---")
    cursor.execute("SELECT id, name, asset_code, organisation_id FROM assets LIMIT 5")
    for row in cursor.fetchall():
        print(row)

    conn.close()

if __name__ == "__main__":
    check_db()
