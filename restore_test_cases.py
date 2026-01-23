import sqlite3
import pandas as pd

CURRENT_DB_PATH = 'eval_results.db'
BACKUP_DB_PATH = 'eval_results_backup.db'

def restore_test_cases():
    print(f"Starting test case restoration from {BACKUP_DB_PATH} to {CURRENT_DB_PATH}")
    
    try:
        # 1. 从备份数据库读取测试用例
        backup_conn = sqlite3.connect(BACKUP_DB_PATH)
        backup_df = pd.read_sql_query("SELECT * FROM test_cases", backup_conn)
        backup_conn.close()
        print(f"Found {len(backup_df)} test cases in backup.")

        if backup_df.empty:
            print("No test cases found in the backup database. Restoration skipped.")
            return

        # 2. 连接到当前数据库
        current_conn = sqlite3.connect(CURRENT_DB_PATH)
        cursor = current_conn.cursor()
        
        # 3. 清空当前数据库的 test_cases 表（确保不重复）
        cursor.execute("DELETE FROM test_cases")
        cursor.execute("DELETE FROM sqlite_sequence WHERE name='test_cases'") # 重置自增ID
        print("Cleared existing test cases in current database.")

        # 4. 将备份数据插入当前数据库
        # 注意：这里需要手动处理created_at，因为pandas的to_sql可能不直接支持DEFAULT CURRENT_TIMESTAMP
        for index, row in backup_df.iterrows():
            cursor.execute('''
                INSERT INTO test_cases (id, title, category, source_code, prompt, reference_answer, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (row['id'], row['title'], row['category'], row['source_code'], row['prompt'], row['reference_answer'], row['created_at']))
        
        current_conn.commit()
        current_conn.close()
        print(f"Successfully restored {len(backup_df)} test cases.")
        print("Test case restoration completed.")

    except Exception as e:
        print(f"Error during test case restoration: {e}")
        if 'current_conn' in locals() and current_conn:
            current_conn.rollback()
            current_conn.close()
        if 'backup_conn' in locals() and backup_conn:
            backup_conn.close()

if __name__ == "__main__":
    restore_test_cases()
