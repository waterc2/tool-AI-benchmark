import sqlite3
import shutil
from datetime import datetime

DB_PATH = 'eval_results.db'
BACKUP_PATH = f'eval_results_backup_{datetime.now().strftime("%Y%m%d_%H%M%S")}.db'

print("=" * 80)
print("数据库迁移脚本：删除 is_remote 字段")
print("=" * 80)

# 1. 备份数据库
print(f"\n📦 步骤 1: 备份数据库到 {BACKUP_PATH}")
shutil.copy2(DB_PATH, BACKUP_PATH)
print(f"✅ 备份完成")

# 2. 连接数据库
print(f"\n🔌 步骤 2: 连接数据库")
conn = sqlite3.connect(DB_PATH)
cursor = conn.cursor()
print("✅ 连接成功")

# 3. 检查当前表结构
print(f"\n🔍 步骤 3: 检查当前表结构")
cursor.execute("PRAGMA table_info(eval_records)")
columns_before = cursor.fetchall()
print(f"当前字段数: {len(columns_before)}")
for col in columns_before:
    print(f"  - {col[1]} ({col[2]})")

# 4. 创建新表（不包含 is_remote 字段）
print(f"\n🏗️  步骤 4: 创建新表结构（不含 is_remote 字段）")
cursor.execute('''
    CREATE TABLE eval_records_new (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        case_id INTEGER NOT NULL,
        model_name TEXT,
        temperature REAL DEFAULT 0.7,
        local_response TEXT,
        chain_of_thought TEXT,
        prompt_tokens INTEGER,
        completion_tokens INTEGER,
        total_time_ms REAL,
        tokens_per_second REAL,
        prompt_tps REAL,
        max_context INTEGER,
        eval_score INTEGER DEFAULT 0,
        eval_comment TEXT,
        eval_score_super INTEGER DEFAULT 0,
        eval_comment_super TEXT,
        eval_score_high INTEGER DEFAULT 0,
        eval_comment_high TEXT,
        eval_score_low INTEGER DEFAULT 0,
        eval_comment_low TEXT,
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (case_id) REFERENCES test_cases(id)
    )
''')
print("✅ 新表创建成功")

# 5. 复制数据（排除 is_remote 字段）
print(f"\n📋 步骤 5: 复制数据到新表")
cursor.execute('''
    INSERT INTO eval_records_new (
        id, case_id, model_name, temperature, local_response,
        chain_of_thought, prompt_tokens, completion_tokens,
        total_time_ms, tokens_per_second, prompt_tps, max_context,
        eval_score, eval_comment,
        eval_score_super, eval_comment_super,
        eval_score_high, eval_comment_high,
        eval_score_low, eval_comment_low,
        created_at
    )
    SELECT 
        id, case_id, model_name, temperature, local_response,
        chain_of_thought, prompt_tokens, completion_tokens,
        total_time_ms, tokens_per_second, prompt_tps, max_context,
        eval_score, eval_comment,
        eval_score_super, eval_comment_super,
        eval_score_high, eval_comment_high,
        eval_score_low, eval_comment_low,
        created_at
    FROM eval_records
''')
rows_copied = cursor.rowcount
print(f"✅ 已复制 {rows_copied} 条记录")

# 6. 删除旧表
print(f"\n🗑️  步骤 6: 删除旧表")
cursor.execute("DROP TABLE eval_records")
print("✅ 旧表已删除")

# 7. 重命名新表
print(f"\n✏️  步骤 7: 重命名新表")
cursor.execute("ALTER TABLE eval_records_new RENAME TO eval_records")
print("✅ 新表已重命名为 eval_records")

# 8. 验证新表结构
print(f"\n✅ 步骤 8: 验证新表结构")
cursor.execute("PRAGMA table_info(eval_records)")
columns_after = cursor.fetchall()
print(f"新字段数: {len(columns_after)}")
for col in columns_after:
    print(f"  - {col[1]} ({col[2]})")

# 9. 验证数据完整性
print(f"\n🔍 步骤 9: 验证数据完整性")
cursor.execute("SELECT COUNT(*) FROM eval_records")
count_after = cursor.fetchone()[0]
print(f"记录总数: {count_after}")

# 确认 is_remote 字段已被删除
has_is_remote = any(col[1] == 'is_remote' for col in columns_after)
if has_is_remote:
    print("❌ 错误：is_remote 字段仍然存在！")
else:
    print("✅ 确认：is_remote 字段已成功删除")

# 10. 提交更改
print(f"\n💾 步骤 10: 提交更改")
conn.commit()
conn.close()
print("✅ 更改已提交，数据库连接已关闭")

print("\n" + "=" * 80)
print("🎉 数据库迁移完成！")
print("=" * 80)
print(f"\n📊 迁移总结:")
print(f"  - 备份文件: {BACKUP_PATH}")
print(f"  - 迁移前字段数: {len(columns_before)}")
print(f"  - 迁移后字段数: {len(columns_after)}")
print(f"  - 复制记录数: {rows_copied}")
print(f"  - 验证记录数: {count_after}")
print(f"\n✅ 所有步骤成功完成！")
