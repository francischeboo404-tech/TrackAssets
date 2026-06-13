import sqlite3
import traceback

def update_db():
    conn = sqlite3.connect('trackit_dev.db')
    cursor = conn.cursor()
    
    queries = [
        "ALTER TABLE transfer_requests ADD COLUMN item_type VARCHAR(20) DEFAULT 'asset'",
        "ALTER TABLE transfer_requests ADD COLUMN inventory_item_id INTEGER",
        "ALTER TABLE transfer_requests ADD COLUMN quantity INTEGER DEFAULT 1",
    ]
    
    for query in queries:
        try:
            cursor.execute(query)
            print(f"Success: {query}")
        except Exception as e:
            print(f"Failed: {query}")
            traceback.print_exc()

    conn.commit()
    conn.close()

if __name__ == "__main__":
    update_db()
