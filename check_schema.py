import sqlite3

def check_schema():
    conn = sqlite3.connect('eval_results.db')
    cursor = conn.cursor()
    
    try:
        cursor.execute("PRAGMA table_info(eval_records)")
        columns = cursor.fetchall()
        print("Current columns in eval_records:")
        for col in columns:
            print(f"- {col[1]} ({col[2]})")
            
        required_columns = [
            'eval_score_super', 'eval_comment_super',
            'eval_score_high', 'eval_comment_high',
            'eval_score_low', 'eval_comment_low'
        ]
        
        existing_column_names = [col[1] for col in columns]
        missing_columns = [col for col in required_columns if col not in existing_column_names]
        
        if missing_columns:
            print("\nMissing columns:")
            for col in missing_columns:
                print(f"- {col}")
        else:
            print("\nAll required columns are present.")
            
    except Exception as e:
        print(f"Error: {e}")
    finally:
        conn.close()

if __name__ == "__main__":
    check_schema()
