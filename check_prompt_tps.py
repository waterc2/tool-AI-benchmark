import sqlite3

conn = sqlite3.connect('eval_results.db')
cursor = conn.cursor()

print("=== Table Schema ===")
cursor.execute("PRAGMA table_info(eval_records)")
for row in cursor.fetchall():
    print(row)

print("\n=== Sample Data ===")
cursor.execute("SELECT id, model_name, prompt_tps, tokens_per_second, total_time_ms, prompt_tokens, completion_tokens FROM eval_records LIMIT 10")
for row in cursor.fetchall():
    print(row)

print("\n=== Prompt TPS Statistics ===")
cursor.execute("SELECT COUNT(*) as total, COUNT(prompt_tps) as has_prompt_tps, AVG(prompt_tps) as avg_prompt_tps FROM eval_records")
stats = cursor.fetchone()
print(f"Total records: {stats[0]}")
print(f"Records with prompt_tps: {stats[1]}")
print(f"Average prompt_tps: {stats[2]}")

print("\n=== Non-null prompt_tps values ===")
cursor.execute("SELECT id, model_name, prompt_tps FROM eval_records WHERE prompt_tps IS NOT NULL AND prompt_tps > 0 LIMIT 10")
for row in cursor.fetchall():
    print(row)

conn.close()
