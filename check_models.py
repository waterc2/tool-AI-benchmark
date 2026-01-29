import sqlite3

# 连接数据库
conn = sqlite3.connect('eval_results.db')
cursor = conn.cursor()

# 查询所有不同的模型名称
cursor.execute('SELECT DISTINCT model_name, COUNT(*) as count FROM eval_records GROUP BY model_name ORDER BY model_name')
models = cursor.fetchall()

print("📊 当前数据库中的模型列表：\n")
print(f"{'模型名称':<50} {'记录数':<10} {'类型判断'}")
print("=" * 80)

for model_name, count in models:
    if model_name.endswith('.gguf'):
        model_type = "本地模型"
    else:
        model_type = "远端模型"
    print(f"{model_name:<50} {count:<10} {model_type}")

# 统计
cursor.execute('SELECT COUNT(DISTINCT model_name) FROM eval_records WHERE model_name LIKE "%.gguf"')
local_count = cursor.fetchone()[0]

cursor.execute('SELECT COUNT(DISTINCT model_name) FROM eval_records WHERE model_name NOT LIKE "%.gguf"')
remote_count = cursor.fetchone()[0]

conn.close()

print("\n" + "=" * 80)
print(f"📈 统计：本地模型 {local_count} 个，远端模型 {remote_count} 个")
