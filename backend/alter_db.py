import sqlite3
import json

def update_db():
    conn = sqlite3.connect('trackit_dev.db')
    cursor = conn.cursor()
    
    try:
        cursor.execute("ALTER TABLE organizations ADD COLUMN logo_url VARCHAR(512);")
        print("Added logo_url column.")
    except Exception as e:
        print("Could not add logo_url (might already exist):", e)

    try:
        cursor.execute("ALTER TABLE organizations ADD COLUMN preferences JSON DEFAULT '{}';")
        print("Added preferences column.")
    except Exception as e:
        print("Could not add preferences (might already exist):", e)
        
    conn.commit()
    conn.close()

if __name__ == "__main__":
    update_db()
