import sqlite3
import pandas as pd
import json

DB_PATH = 'eval_results.db'

def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA foreign_keys = ON")
    return conn

# --- 测试用例 (Test Cases) 管理 ---

def save_test_case(title, category, source_code_dict, prompt, reference_answer, case_id=None):
    """保存或更新测试用例"""
    conn = get_connection()
    cursor = conn.cursor()
    
    # 将多文件字典转换为 JSON 字符串
    source_code_json = json.dumps(source_code_dict)
    
    if case_id:
        cursor.execute('''
            UPDATE test_cases 
            SET title = ?, category = ?, source_code = ?, prompt = ?, reference_answer = ?
            WHERE id = ?
        ''', (title, category, source_code_json, prompt, reference_answer, case_id))
    else:
        cursor.execute('''
            INSERT INTO test_cases (title, category, source_code, prompt, reference_answer)
            VALUES (?, ?, ?, ?, ?)
        ''', (title, category, source_code_json, prompt, reference_answer))
    
    conn.commit()
    conn.close()

def get_all_test_cases():
    """获取所有测试用例"""
    conn = get_connection()
    query = "SELECT * FROM test_cases ORDER BY created_at DESC"
    df = pd.read_sql_query(query, conn)
    conn.close()
    return df

def delete_test_case(case_id):
    """删除测试用例及其关联的评测记录"""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM eval_records WHERE case_id = ?", (case_id,))
    cursor.execute("DELETE FROM test_cases WHERE id = ?", (case_id,))
    conn.commit()
    conn.close()

def delete_eval_record(record_id):
    """删除单条评测记录"""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM eval_records WHERE id = ?", (record_id,))
    conn.commit()
    conn.close()

def get_safe_result(res, key, default):
    """Safely retrieve a key from a dictionary, checking if res is a dict first."""
    return res.get(key, default) if isinstance(res, dict) else default

def update_eval_scores(record_id, eval_results):
    """更新评测记录的评分和评语"""
    conn = get_connection()
    cursor = conn.cursor()
    
    # 计算平均分 (使用安全访问，并确保转换为数值类型)
    super_score = float(get_safe_result(eval_results.get('super', {}), 'score', 0))
    high_score = float(get_safe_result(eval_results.get('high', {}), 'score', 0))
    low_score = float(get_safe_result(eval_results.get('low', {}), 'score', 0))
    
    # 加权平均分: Super 50%, High 30%, Low 20%
    avg_score = (super_score * 0.5) + (high_score * 0.3) + (low_score * 0.2)
    
    cursor.execute('''
        UPDATE eval_records
        SET eval_score = ?,
            eval_comment = ?,
            eval_score_super = ?,
            eval_comment_super = ?,
            eval_score_high = ?,
            eval_comment_high = ?,
            eval_score_low = ?,
            eval_comment_low = ?
        WHERE id = ?
    ''', (
        avg_score,
        "Multi-evaluator result",
        super_score,
        get_safe_result(eval_results.get('super', {}), 'reasoning', ""),
        high_score,
        get_safe_result(eval_results.get('high', {}), 'reasoning', ""),
        low_score,
        get_safe_result(eval_results.get('low', {}), 'reasoning', ""),
        record_id
    ))
    
    conn.commit()
    conn.close()

# --- 评测记录 (Eval Records) 管理 ---

def save_eval_record(data):
    """保存评测记录"""
    print(f"[DEBUG] Saving eval record for case_id: {data.get('case_id')}")
    conn = get_connection()
    cursor = conn.cursor()
    
    fields = [
        'case_id', 'model_name', 'temperature', 'local_response',
        'chain_of_thought', 'prompt_tokens', 'completion_tokens',
        'total_time_ms', 'tokens_per_second', 'prompt_tps', 'max_context',
        'eval_score', 'eval_comment',
        'eval_score_super', 'eval_comment_super',
        'eval_score_high', 'eval_comment_high',
        'eval_score_low', 'eval_comment_low'
    ]
    
    placeholders = ', '.join(['?' for _ in fields])
    columns = ', '.join(fields)
    values = [data.get(field) for field in fields]
    # 确保 case_id 是整数，防止 pandas/numpy 类型导致 BLOB 存储
    if 'case_id' in fields:
        idx = fields.index('case_id')
        if values[idx] is not None:
            values[idx] = int(values[idx])
    
    query = f"INSERT INTO eval_records ({columns}) VALUES ({placeholders})"
    
    try:
        cursor.execute(query, values)
        conn.commit()
        print(f"[DEBUG] Eval record saved successfully. ID: {cursor.lastrowid}")
    except Exception as e:
        print(f"[ERROR] Failed to save eval record: {str(e)}")
        raise e
    finally:
        conn.close()

def get_eval_history(case_id=None, model_name=None):
    """获取评测历史，可选按 case_id 和 model_name 筛选"""
    conn = get_connection()
    query = """
        SELECT r.*, c.title as case_title, c.prompt, c.reference_answer
        FROM eval_records r
        JOIN test_cases c ON r.case_id = c.id
        WHERE 1=1
    """
    params = []
    if case_id is not None:
        query += " AND r.case_id = ?"
        params.append(int(case_id))
    if model_name and model_name != "全部":
        query += " AND r.model_name = ?"
        params.append(model_name)

    query += " ORDER BY r.created_at DESC"

    df = pd.read_sql_query(query, conn, params=params)
    conn.close()
    return df

def get_all_models():
    """获取所有已记录的模型名称"""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT DISTINCT model_name FROM eval_records WHERE model_name IS NOT NULL")
    models = [row[0] for row in cursor.fetchall()]
    conn.close()
    return models

def get_stats():
    """获取全局统计指标"""
    conn = get_connection()
    cursor = conn.cursor()
    
    stats = {}
    # 计算三个评委的综合平均分 (Weighted Average: 50/30/20)
    cursor.execute("""
        SELECT AVG(
            0.5 * COALESCE(eval_score_super, eval_score*10, 0) + 
            0.3 * COALESCE(eval_score_high, eval_score*10, 0) + 
            0.2 * COALESCE(eval_score_low, eval_score*10, 0)
        ) FROM eval_records
    """)
    stats['avg_score'] = cursor.fetchone()[0] or 0
    
    cursor.execute("SELECT AVG(tokens_per_second) FROM eval_records")
    stats['avg_tps'] = cursor.fetchone()[0] or 0
    
    cursor.execute("SELECT COUNT(*) FROM eval_records")
    stats['total_evals'] = cursor.fetchone()[0] or 0
    
    cursor.execute("SELECT COUNT(*) FROM test_cases")
    stats['total_cases'] = cursor.fetchone()[0] or 0
    
    conn.close()
    return stats

def get_model_summary_stats():
    """以模型为单位的汇总统计"""
    conn = get_connection()
    query = """
        SELECT model_name, 
               AVG(0.5 * COALESCE(eval_score_super, eval_score*10, 0) + 
                   0.3 * COALESCE(eval_score_high, eval_score*10, 0) + 
                   0.2 * COALESCE(eval_score_low, eval_score*10, 0)) as avg_score, 
               COUNT(*) as test_count
        FROM eval_records
        GROUP BY model_name
        ORDER BY avg_score DESC
    """
    df = pd.read_sql_query(query, conn)
    conn.close()
    return df

def get_model_detail_stats(model_name):
    """特定模型在各个用例下的平均分及详细指标"""
    conn = get_connection()
    query = """
        SELECT c.title as case_title, 
               AVG(0.5 * COALESCE(r.eval_score_super, r.eval_score*10, 0) + 
                   0.3 * COALESCE(r.eval_score_high, r.eval_score*10, 0) + 
                   0.2 * COALESCE(r.eval_score_low, r.eval_score*10, 0)) as avg_score,
               AVG(COALESCE(r.eval_score_super, 0)) as avg_score_super,
               AVG(COALESCE(r.eval_score_high, 0)) as avg_score_high,
               AVG(COALESCE(r.eval_score_low, 0)) as avg_score_low,
               AVG(r.completion_tokens) as avg_completion_tokens,
               AVG(r.prompt_tokens) as avg_prompt_tokens,
               AVG(r.total_time_ms) as avg_total_time_ms,
               AVG(r.tokens_per_second) as avg_tps,
               AVG(r.prompt_tps) as avg_prompt_tps,
               COUNT(*) as run_count
        FROM eval_records r
        JOIN test_cases c ON r.case_id = c.id
        WHERE r.model_name = ?
        GROUP BY r.case_id
        ORDER BY avg_score DESC
    """
    df = pd.read_sql_query(query, conn, params=(model_name,))
    conn.close()
    return df

def get_case_summary_stats():
    """以测试题为单位的汇总统计"""
    conn = get_connection()
    query = """
        SELECT c.id as case_id, c.title as case_title, 
               AVG(0.5 * COALESCE(r.eval_score_super, r.eval_score*10, 0) + 
                   0.3 * COALESCE(r.eval_score_high, r.eval_score*10, 0) + 
                   0.2 * COALESCE(r.eval_score_low, r.eval_score*10, 0)) as avg_score, 
               COUNT(*) as total_runs
        FROM eval_records r
        JOIN test_cases c ON r.case_id = c.id
        GROUP BY c.id
        ORDER BY avg_score DESC
    """
    df = pd.read_sql_query(query, conn)
    conn.close()
    return df

def get_case_model_ranking(case_id):
    """特定测试题下各模型的排名"""
    conn = get_connection()
    query = """
        SELECT model_name, 
               AVG(0.5 * COALESCE(eval_score_super, eval_score*10, 0) + 
                   0.3 * COALESCE(eval_score_high, eval_score*10, 0) + 
                   0.2 * COALESCE(eval_score_low, eval_score*10, 0)) as avg_score, 
               COUNT(*) as run_count
        FROM eval_records
        WHERE case_id = ?
        GROUP BY model_name
        ORDER BY avg_score DESC
    """
    df = pd.read_sql_query(query, conn, params=(case_id,))
    conn.close()
    return df

def get_model_speed_ranking():
    """获取模型速度排行（按平均耗时升序排序）"""
    conn = get_connection()
    query = """
        SELECT model_name, 
               AVG(total_time_ms) as avg_total_time_ms,
               AVG(tokens_per_second) as avg_tps, 
               AVG(prompt_tps) as avg_prompt_tps,
               COUNT(*) as test_count
        FROM eval_records
        WHERE total_time_ms > 0
        GROUP BY model_name
        ORDER BY avg_total_time_ms ASC
    """
    df = pd.read_sql_query(query, conn)
    conn.close()
    return df
