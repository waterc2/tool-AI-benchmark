import sqlite3
import pandas as pd
import json
import streamlit as st

DB_PATH = 'eval_results.db'

def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def is_remote_model(model_name):
    """判断是否为远端模型（基于模型名称）
    
    规则：
    - 本地模型：以 .gguf 结尾
    - 远端模型：不以 .gguf 结尾
    
    Args:
        model_name: 模型名称
        
    Returns:
        bool: True 表示远端模型，False 表示本地模型
    """
    if not model_name:
        return False
    return not model_name.endswith('.gguf')


def clear_cache():
    """清除所有 Streamlit 数据缓存"""
    st.cache_data.clear()


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
    clear_cache()  # 清除缓存以反映新数据


@st.cache_data(ttl=60)
def get_all_test_cases():
    """获取所有测试用例（缓存60秒）"""
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
    clear_cache()

def delete_eval_record(record_id):
    """删除单条评测记录"""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM eval_records WHERE id = ?", (record_id,))
    conn.commit()
    conn.close()
    clear_cache()

def get_safe_result(res, key, default):
    """Safely retrieve a key from a dictionary, checking if res is a dict first."""
    return res.get(key, default) if isinstance(res, dict) else default

def update_eval_scores(record_id, eval_results):
    """更新评测记录的评分和评语"""
    conn = get_connection()
    cursor = conn.cursor()
    
    # 获取五种模型的评分 (使用 eval_score_1 到 eval_score_5)
    # 映射: 1=gem, 2=opus, 3=gpt, 4=top2, 5=top
    score_1 = float(get_safe_result(eval_results.get('gem', {}), 'score', 0))
    score_2 = float(get_safe_result(eval_results.get('opus', {}), 'score', 0))
    score_3 = float(get_safe_result(eval_results.get('gpt', {}), 'score', 0))
    score_4 = float(get_safe_result(eval_results.get('top2', {}), 'score', 0))
    score_5 = float(get_safe_result(eval_results.get('top', {}), 'score', 0))
    
    # 计算有效分数（忽略 0 分，即忽略失败的评测）
    # 所有评委评分计入平均分 (gem, opus, gpt, top2, top)
    # 注意：此变更会将历史数据中的 eval_score_4 (top2) 纳入计算
    # 如果历史数据中 top2 评分缺失 (为 0)，可能需要运行数据迁移脚本
    scores = [score_1, score_2, score_3, score_4, score_5]
    valid_scores = [s for s in scores if s > 0]
    
    if valid_scores:
        avg_score = sum(valid_scores) / len(valid_scores)
    else:
        avg_score = 0
    
    cursor.execute('''
        UPDATE eval_records
        SET eval_score = ?,
            eval_comment = ?,
            eval_score_1 = ?,
            eval_comment_1 = ?,
            eval_score_2 = ?,
            eval_comment_2 = ?,
            eval_score_3 = ?,
            eval_comment_3 = ?,
            eval_score_4 = ?,
            eval_comment_4 = ?,
            eval_score_5 = ?,
            eval_comment_5 = ?
        WHERE id = ?
    ''', (
        avg_score,
        "Multi-evaluator result",
        score_1,
        get_safe_result(eval_results.get('gem', {}), 'reasoning', ""),
        score_2,
        get_safe_result(eval_results.get('opus', {}), 'reasoning', ""),
        score_3,
        get_safe_result(eval_results.get('gpt', {}), 'reasoning', ""),
        score_4,
        get_safe_result(eval_results.get('top2', {}), 'reasoning', ""),
        score_5,
        get_safe_result(eval_results.get('top', {}), 'reasoning', ""),
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
        'eval_score_1', 'eval_comment_1',
        'eval_score_2', 'eval_comment_2',
        'eval_score_3', 'eval_comment_3',
        'eval_score_4', 'eval_comment_4',
        'eval_score_5', 'eval_comment_5'
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
        record_id = cursor.lastrowid
        print(f"[DEBUG] Eval record saved successfully. ID: {record_id}")
        return record_id
    except Exception as e:
        print(f"[ERROR] Failed to save eval record: {str(e)}")
        raise e
    finally:
        conn.close()

def get_eval_record_by_id(record_id):
    """根据 ID 获取单条评测记录"""
    conn = get_connection()
    query = """
        SELECT r.*, c.title as case_title, c.prompt, c.reference_answer
        FROM eval_records r
        JOIN test_cases c ON r.case_id = c.id
        WHERE r.id = ?
    """
    df = pd.read_sql_query(query, conn, params=(int(record_id),))
    conn.close()
    return df.iloc[0].to_dict() if not df.empty else None

@st.cache_data(ttl=30)
def get_eval_history(case_id=None, model_name=None):
    """获取评测历史，可选按 case_id 和 model_name 筛选（缓存30秒）"""
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

@st.cache_data(ttl=30)
def get_all_models():
    """获取所有已记录的模型名称（缓存30秒）"""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT DISTINCT model_name FROM eval_records WHERE model_name IS NOT NULL")
    models = [row[0] for row in cursor.fetchall()]
    conn.close()
    return models


@st.cache_data(ttl=10)
def get_stats():
    """获取全局统计指标"""
    conn = get_connection()
    cursor = conn.cursor()
    
    stats = {}
    # 计算五个评委的综合平均分 (gem, opus, gpt, top2, top)
    cursor.execute("""
        SELECT AVG(
            (COALESCE(eval_score_1, 0) + COALESCE(eval_score_2, 0) + 
             COALESCE(eval_score_3, 0) + 
             COALESCE(eval_score_5, 0)) / 
            NULLIF(
                (CASE WHEN eval_score_1 > 0 THEN 1 ELSE 0 END) + 
                (CASE WHEN eval_score_2 > 0 THEN 1 ELSE 0 END) + 
                (CASE WHEN eval_score_3 > 0 THEN 1 ELSE 0 END) + 
                (CASE WHEN eval_score_5 > 0 THEN 1 ELSE 0 END), 
                0
            )
        ) FROM eval_records
        WHERE (COALESCE(eval_score_1, 0) + COALESCE(eval_score_2, 0) + 
               COALESCE(eval_score_3, 0) + 
               COALESCE(eval_score_5, 0)) > 0
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

@st.cache_data(ttl=30)
def get_model_summary_stats(model_type="全部"):
    """以模型为单位的汇总统计（缓存30秒）"""
    conn = get_connection()
    query = """
        SELECT model_name, 
               AVG(
                   (COALESCE(eval_score_1, 0) + COALESCE(eval_score_2, 0) + 
                    COALESCE(eval_score_3, 0) + 
                    COALESCE(eval_score_5, 0)) / 
                   NULLIF(
                       (CASE WHEN eval_score_1 > 0 THEN 1 ELSE 0 END) + 
                       (CASE WHEN eval_score_2 > 0 THEN 1 ELSE 0 END) + 
                       (CASE WHEN eval_score_3 > 0 THEN 1 ELSE 0 END) + 
                       (CASE WHEN eval_score_5 > 0 THEN 1 ELSE 0 END), 
                       0
                   )
               ) as avg_score, 
               COUNT(*) as test_count
        FROM eval_records
        GROUP BY model_name
        ORDER BY avg_score DESC
    """
    df = pd.read_sql_query(query, conn)
    conn.close()
    
    # 根据模型类型过滤
    if model_type == "本地模型":
        df = df[df['model_name'].apply(lambda x: not is_remote_model(x))]
    elif model_type == "远端模型":
        df = df[df['model_name'].apply(lambda x: is_remote_model(x))]
    
    return df


@st.cache_data(ttl=30)
def get_model_detail_stats(model_name):
    """特定模型在各个用例下的平均分及详细指标"""
    conn = get_connection()
    query = """
        SELECT c.title as case_title, 
               AVG(
                   (COALESCE(r.eval_score_1, 0) + COALESCE(r.eval_score_2, 0) + 
                    COALESCE(r.eval_score_3, 0) + 
                    COALESCE(r.eval_score_5, 0)) / 
                   NULLIF(
                       (CASE WHEN r.eval_score_1 > 0 THEN 1 ELSE 0 END) + 
                       (CASE WHEN r.eval_score_2 > 0 THEN 1 ELSE 0 END) + 
                       (CASE WHEN r.eval_score_3 > 0 THEN 1 ELSE 0 END) + 
                       (CASE WHEN r.eval_score_5 > 0 THEN 1 ELSE 0 END), 
                       0
                   )
               ) as avg_score,
               AVG(COALESCE(r.eval_score_1, 0)) as avg_score_1,
               AVG(COALESCE(r.eval_score_2, 0)) as avg_score_2,
               AVG(COALESCE(r.eval_score_3, 0)) as avg_score_3,
               AVG(COALESCE(r.eval_score_4, 0)) as avg_score_4,
               AVG(COALESCE(r.eval_score_5, 0)) as avg_score_5,
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

@st.cache_data(ttl=30)
def get_case_summary_stats(model_type="全部"):
    """以测试题为单位的汇总统计（缓存30秒）"""
    conn = get_connection()
    
    # 先获取所有数据
    if model_type == "全部":
        query = """
            SELECT c.id as case_id, c.title as case_title, 
                   AVG(
                       (COALESCE(r.eval_score_1, 0) + COALESCE(r.eval_score_2, 0) + 
                        COALESCE(r.eval_score_3, 0) + 
                        COALESCE(r.eval_score_5, 0)) / 
                       NULLIF(
                           (CASE WHEN r.eval_score_1 > 0 THEN 1 ELSE 0 END) + 
                           (CASE WHEN r.eval_score_2 > 0 THEN 1 ELSE 0 END) + 
                           (CASE WHEN r.eval_score_3 > 0 THEN 1 ELSE 0 END) + 
                           (CASE WHEN r.eval_score_5 > 0 THEN 1 ELSE 0 END), 
                           0
                       )
                   ) as avg_score, 
                   COUNT(*) as total_runs
            FROM eval_records r
            JOIN test_cases c ON r.case_id = c.id
            GROUP BY c.id
            ORDER BY avg_score DESC
        """
        df = pd.read_sql_query(query, conn)
    else:
        # 需要按模型类型过滤，先获取详细数据
        query = """
            SELECT c.id as case_id, c.title as case_title,
                   r.model_name,
                   (COALESCE(r.eval_score_1, 0) + COALESCE(r.eval_score_2, 0) + 
                    COALESCE(r.eval_score_3, 0) + 
                    COALESCE(r.eval_score_5, 0)) / 
                   NULLIF(
                       (CASE WHEN r.eval_score_1 > 0 THEN 1 ELSE 0 END) + 
                       (CASE WHEN r.eval_score_2 > 0 THEN 1 ELSE 0 END) + 
                       (CASE WHEN r.eval_score_3 > 0 THEN 1 ELSE 0 END) + 
                       (CASE WHEN r.eval_score_5 > 0 THEN 1 ELSE 0 END), 
                       0
                   ) as score
            FROM eval_records r
            JOIN test_cases c ON r.case_id = c.id
        """
        df_raw = pd.read_sql_query(query, conn)
        
        # 根据模型类型过滤
        if model_type == "本地模型":
            df_raw = df_raw[df_raw['model_name'].apply(lambda x: not is_remote_model(x))]
        elif model_type == "远端模型":
            df_raw = df_raw[df_raw['model_name'].apply(lambda x: is_remote_model(x))]
        
        # 聚合统计
        df = df_raw.groupby(['case_id', 'case_title']).agg(
            avg_score=('score', 'mean'),
            total_runs=('score', 'count')
        ).reset_index().sort_values('avg_score', ascending=False)
    
    conn.close()
    return df


@st.cache_data(ttl=30)
def get_case_model_ranking(case_id, model_type="全部"):
    """特定测试题下各模型的排名"""
    conn = get_connection()
    query = """
        SELECT model_name, 
               AVG(COALESCE(eval_score_1, 0)) as avg_score_1,
               AVG(COALESCE(eval_score_2, 0)) as avg_score_2,
               AVG(COALESCE(eval_score_3, 0)) as avg_score_3,
               AVG(COALESCE(eval_score_4, 0)) as avg_score_4,
               AVG(COALESCE(eval_score_5, 0)) as avg_score_5,
                AVG(
                   (COALESCE(eval_score_1, 0) + COALESCE(eval_score_2, 0) + 
                    COALESCE(eval_score_3, 0) + 
                    COALESCE(eval_score_5, 0)) / 
                   NULLIF(
                       (CASE WHEN eval_score_1 > 0 THEN 1 ELSE 0 END) + 
                       (CASE WHEN eval_score_2 > 0 THEN 1 ELSE 0 END) + 
                       (CASE WHEN eval_score_3 > 0 THEN 1 ELSE 0 END) + 
                       (CASE WHEN eval_score_5 > 0 THEN 1 ELSE 0 END), 
                       0
                   )
                ) as avg_score, 
               AVG(total_time_ms) as avg_total_time_ms,
               COUNT(*) as run_count
        FROM eval_records
        WHERE case_id = ?
        GROUP BY model_name
        ORDER BY avg_score DESC
    """
    df = pd.read_sql_query(query, conn, params=[int(case_id)])
    conn.close()
    
    # 根据模型类型过滤
    if model_type == "本地模型":
        df = df[df['model_name'].apply(lambda x: not is_remote_model(x))]
    elif model_type == "远端模型":
        df = df[df['model_name'].apply(lambda x: is_remote_model(x))]
    
    return df


@st.cache_data(ttl=30)
def get_model_speed_ranking(model_type="全部"):
    """获取模型速度排行（按平均耗时升序排序，缓存30秒）"""
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
    
    # 根据模型类型过滤
    if model_type == "本地模型":
        df = df[df['model_name'].apply(lambda x: not is_remote_model(x))]
    elif model_type == "远端模型":
        df = df[df['model_name'].apply(lambda x: is_remote_model(x))]
    
    return df
