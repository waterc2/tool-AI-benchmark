import sqlite3
import sys

def init_db():
    """初始化数据库，创建测试用例表和评测记录表"""
    # 强制设置 stdout 编码为 UTF-8，解决 Windows 终端中文乱码问题
    if sys.stdout.encoding != 'utf-8':
        sys.stdout.reconfigure(encoding='utf-8')
        
    conn = sqlite3.connect('eval_results.db')
    cursor = conn.cursor()

    # 创建测试用例表
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS test_cases (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,                -- 测试用例标题
            category TEXT,                      -- 类型/分类
            source_code TEXT,                   -- 源代码（JSON格式存储多文件）
            prompt TEXT NOT NULL,               -- 修改要求/提示词
            reference_answer TEXT,              -- 参考答案
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    # 创建评测记录表（重构版）
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS eval_records (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            
            -- 关联测试用例
            case_id INTEGER,                    -- 外键，关联 test_cases.id
            
            -- 模型信息
            model_name TEXT,                    -- 模型标识
            temperature REAL DEFAULT 0.7,       -- 生成温度
            
            -- 模型输出
            local_response TEXT,                -- 本地模型生成的代码
            chain_of_thought TEXT,              -- 思维链内容（CoT）
            
            -- 性能指标
            prompt_tokens INTEGER,              -- 输入 token 数
            completion_tokens INTEGER,          -- 输出 token 数
            total_time_ms REAL,                 -- 总耗时(毫秒)
            tokens_per_second REAL,             -- 生成速度 (tokens/s)
            prompt_tps REAL,                    -- 预读速度 (tokens/s)
            max_context INTEGER,                -- 模型支持的最大上下文
            
            -- 评分与反馈
            eval_score INTEGER,                 -- 评分 (旧版 0-10)
            eval_comment TEXT,                  -- 评语 (旧版)
            eval_score_super INTEGER,           -- super 评委评分 (0-100)
            eval_comment_super TEXT,            -- super 评委评语
            eval_score_high INTEGER,            -- high 评委评分 (0-100)
            eval_comment_high TEXT,             -- high 评委评语
            eval_score_low INTEGER,             -- low 评委评分 (0-100)
            eval_comment_low TEXT,              -- low 评委评语
            
            -- 元数据
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            
            FOREIGN KEY (case_id) REFERENCES test_cases(id) ON DELETE CASCADE
        )
    ''')

    conn.commit()
    conn.close()
    print("数据库初始化成功！")
    print("   - test_cases 表已创建")
    print("   - eval_records 表已创建")

if __name__ == "__main__":
    init_db()
