import sqlite3

def inspect_db(db_path):
    print(f"Inspecting {db_path}...")
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
    tables = cursor.fetchall()
    print(f"Tables found: {tables}")
    
    for table_name_tup in tables:
        table_name = table_name_tup[0]
        cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
        count = cursor.fetchone()[0]
        print(f"Table {table_name}: {count} records")
        
        # Check date range if it's eval_records
        if table_name == 'eval_records':
            cursor.execute("SELECT MIN(created_at), MAX(created_at) FROM eval_records")
            date_range = cursor.fetchone()
            print(f"  Date range: {date_range}")
            
            # Count records per day
            cursor.execute("SELECT date(created_at), count(*) FROM eval_records GROUP BY date(created_at) ORDER BY date(created_at) DESC")
            daily = cursor.fetchall()
            print(f"  Daily breakdown: {daily}")
            
    conn.close()

if __name__ == "__main__":
    inspect_db('eval_results.db')
