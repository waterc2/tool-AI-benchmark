"""
数据库迁移脚本：将旧的评分字段映射到新的评分字段
并删除旧的字段，保证数据不丢失
"""
import sqlite3
import sys

# 数据库路径
DB_PATH = 'eval_results.db'

# 映射关系：旧字段名 -> 新字段名
FIELD_MAPPING = {
    'eval_score_gem': 'eval_score_1',
    'eval_score_opus': 'eval_score_2',
    'eval_score_gpt': 'eval_score_3',
    'eval_score_top2': 'eval_score_4',
    'eval_score_top': 'eval_score_5',
    'eval_comment_gem': 'eval_comment_1',
    'eval_comment_opus': 'eval_comment_2',
    'eval_comment_gpt': 'eval_comment_3',
    'eval_comment_top2': 'eval_comment_4',
    'eval_comment_top': 'eval_comment_5',
}

def get_table_columns(cursor, table_name):
    """获取指定表的列名列表"""
    cursor.execute(f"PRAGMA table_info({table_name})")
    return [col[1] for col in cursor.fetchall()]

def migrate_database():
    """执行数据库迁移"""
    print(f"正在连接数据库: {DB_PATH}")
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    try:
        # 初始检查字段
        old_columns = get_table_columns(cursor, 'eval_records')
        
        print("\n当前数据库中的旧评分相关字段:")
        for old_col in FIELD_MAPPING.keys():
            if old_col in old_columns:
                print(f"  - {old_col}")
        
        # 1. 添加所有新的目标字段 (eval_score_1 到 eval_score_5)
        print("\n步骤 1: 添加所有新的目标字段...")
        required_new_cols = list(FIELD_MAPPING.values())
        
        # 重新获取当前字段列表，因为在循环中可能会被修改
        current_cols = get_table_columns(cursor, 'eval_records')
        
        for new_col in required_new_cols:
            if new_col not in current_cols:
                try:
                    # ALTER TABLE 在 SQLite 中是 DDL，通常是隐式提交的，但为了安全，我们单独提交
                    cursor.execute(f"ALTER TABLE eval_records ADD COLUMN {new_col} REAL DEFAULT 0")
                    conn.commit()
                    print(f"  ✓ 已添加字段: {new_col}")
                    current_cols.append(new_col) # 更新列表
                except Exception as e:
                    print(f"  ✗ 添加字段 {new_col} 失败: {str(e)}")
                    raise
            else:
                print(f"  - 字段已存在: {new_col}")
        
        # 重新获取最新的字段列表
        new_columns = get_table_columns(cursor, 'eval_records')
        
        print("\n当前数据库中的新评分相关字段:")
        for new_col in FIELD_MAPPING.values():
            if new_col in new_columns:
                print(f"  - {new_col}")
        
        # 2. 映射旧数据到新字段 (使用事务保证数据映射一致性)
        print("\n步骤 2: 映射旧数据到新字段...")
        conn.execute("BEGIN TRANSACTION")
        
        for old_col, new_col in FIELD_MAPPING.items():
            # 只有当旧字段和新字段都存在时才进行映射
            if old_col in old_columns and new_col in new_columns:
                cursor.execute(f"""
                    UPDATE eval_records 
                    SET {new_col} = {old_col}
                    WHERE {old_col} IS NOT NULL AND {old_col} != 0
                """)
                affected_rows = cursor.rowcount
                print(f"  ✓ 已映射 {affected_rows} 条记录: {old_col} -> {new_col}")
            elif new_col in new_columns:
                print(f"  - 跳过映射: 旧字段 {old_col} 不存在")
        
        # 3. 验证数据迁移 (只验证存在的字段)
        print("\n步骤 3: 验证数据迁移...")
        
        validation_success = True
        for i in range(1, 6):
            score_col = f'eval_score_{i}'
            if score_col in new_columns:
                cursor.execute(f"SELECT COUNT(*) FROM eval_records WHERE {score_col} IS NOT NULL AND {score_col} != 0")
                count = cursor.fetchone()[0]
                print(f"  ✓ {score_col} (评委 {i}): {count} 条记录")
            else:
                print(f"  - 跳过验证: 字段 {score_col} 不存在")
        
        # 4. 删除旧字段
        print("\n步骤 4: 删除旧字段...")
        for old_col in FIELD_MAPPING.keys():
            if old_col in old_columns:
                try:
                    cursor.execute(f"ALTER TABLE eval_records DROP COLUMN {old_col}")
                    print(f"  ✓ 已删除字段: {old_col}")
                except Exception as e:
                    print(f"  ✗ 删除字段 {old_col} 失败: {str(e)}")
                    validation_success = False
        
        if validation_success:
            conn.commit()
            print("\n✅ 数据库迁移完成！")
        else:
            conn.rollback()
            print("\n❌ 迁移失败，已回滚数据映射和删除操作。")
            return False
        
        # 最终显示迁移后的字段列表
        cursor.execute("PRAGMA table_info(eval_records)")
        columns = cursor.fetchall()
        print("\n迁移后的评分相关字段:")
        for col in columns:
            col_name = col[1]
            if col_name.startswith('eval_score') or col_name.startswith('eval_comment'):
                print(f"  - {col_name}")
        
    except Exception as e:
        print(f"\n❌ 迁移失败: {str(e)}")
        conn.rollback()
        return False
    
    finally:
        conn.close()
    
    return True

if __name__ == "__main__":
    print("=" * 60)
    print("数据库评分字段迁移脚本")
    print("=" * 60)
    
    success = migrate_database()
    
    if success:
        print("\n" + "=" * 60)
        print("迁移成功！现在可以运行应用了。")
        print("=" * 60)
        sys.exit(0)
    else:
        print("\n" + "=" * 60)
        print("迁移失败，请检查错误信息。")
        print("=" * 60)
        sys.exit(1)