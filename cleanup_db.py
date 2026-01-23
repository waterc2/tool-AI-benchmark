import sqlite3

DB_PATH = 'eval_results.db'

def cleanup_db():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    print(f"Starting database cleanup: {DB_PATH}")
    
    # Check if tables exist
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='eval_records'")
    if not cursor.fetchone():
        print("Error: eval_records table does not exist.")
        conn.close()
        return
    
    # Delete all evaluation records
    cursor.execute("DELETE FROM eval_records")
    deleted_records = cursor.rowcount
    print(f"Deleted {deleted_records} evaluation records")
    
    # Reset auto-increment counter for eval_records
    cursor.execute("DELETE FROM sqlite_sequence WHERE name='eval_records'")
    print("Reset auto-increment counter for eval_records")
    
    # NOTE: Retaining test_cases as per user request.
    
    conn.commit()
    conn.close()
    print("Database cleanup completed successfully.")

if __name__ == "__main__":
    cleanup_db()
