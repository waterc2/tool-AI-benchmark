#!/usr/bin/env python3
"""
删除指定模型的测试记录脚本

用法:
    python delete_model_records.py <model_name>
    python delete_model_records.py  # 使用默认模型名

示例:
    python delete_model_records.py Qwen3.5-27B-UD-Q5_K_XL.gguf
"""

import sqlite3
import sys

DB_PATH = 'eval_results.db'
DEFAULT_MODEL = 'Qwen3.5-27B-UD-Q5_K_XL.gguf'


def delete_model_records(model_name: str) -> int:
    """
    删除指定模型的所有评测记录
    
    Args:
        model_name: 要删除的模型名称
        
    Returns:
        删除的记录数量
    """
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # 先查询有多少条记录
    cursor.execute("SELECT COUNT(*) FROM eval_records WHERE model_name = ?", (model_name,))
    count = cursor.fetchone()[0]
    
    if count == 0:
        print(f"未找到模型 '{model_name}' 的测试记录")
        conn.close()
        return 0
    
    # 删除记录
    cursor.execute("DELETE FROM eval_records WHERE model_name = ?", (model_name,))
    conn.commit()
    conn.close()
    
    print(f"已成功删除模型 '{model_name}' 的 {count} 条测试记录")
    return count


def main():
    # 获取模型名称（从命令行参数或使用默认值）
    if len(sys.argv) > 1:
        model_name = sys.argv[1]
    else:
        model_name = DEFAULT_MODEL
        print(f"未指定模型名称，使用默认值: {model_name}")
    
    # 确认删除
    print(f"即将删除模型 '{model_name}' 的所有测试记录")
    confirm = input("确认删除? (y/N): ").strip().lower()
    
    if confirm == 'y':
        deleted = delete_model_records(model_name)
        print(f"操作完成，共删除 {deleted} 条记录")
    else:
        print("操作已取消")


if __name__ == "__main__":
    main()