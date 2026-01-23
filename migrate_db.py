import sqlite3

DB_PATH = 'eval_results.db'

def migrate_db():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    print(f"Starting database migration: {DB_PATH}")
    
    # Check if eval_records table exists
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='eval_records'")
    if not cursor.fetchone():
        print("Error: eval_records table does not exist. Please run init_db.py first.")
        conn.close()
        return

    # Migration steps: add missing evaluator columns
    migrations = [
        ("eval_score_super", "INTEGER"),
        ("eval_comment_super", "TEXT"),
        ("eval_score_high", "INTEGER"),
        ("eval_comment_high", "TEXT"),
        ("eval_score_low", "INTEGER"),
        ("eval_comment_low", "TEXT"),
    ]
    
    for column_name, column_type in migrations:
        try:
            # 检查列是否已存在
            cursor.execute(f"PRAGMA table_info(eval_records)")
            existing_columns = [col[1] for col in cursor.fetchall()]
            
            if column_name not in existing_columns:
                alter_query = f"ALTER TABLE eval_records ADD COLUMN {column_name} {column_type}"
                cursor.execute(alter_query)
                print(f"Successfully added column: {column_name}")
            else:
                print(f"Skipped: column {column_name} already exists")
        except sqlite3.OperationalError as e:
            print(f"Migration failed (column: {column_name}): {e}")
            conn.rollback()
            conn.close()
            return

    conn.commit()
    conn.close()
    print("Database migration completed.")

if __name__ == "__main__":
    migrate_db()
