import sqlite3
import sys

def init_db(clear_records=False):
    """初始化数据库，创建测试用例表和评测记录表"""
    # 强制设置 stdout 编码为 UTF-8，解决 Windows 终端中文乱码问题
    if sys.stdout.encoding != 'utf-8':
        sys.stdout.reconfigure(encoding='utf-8')
        
    conn = sqlite3.connect('eval_results.db')
    cursor = conn.cursor()

    # 如果需要清空记录，删除评测记录表
    if clear_records:
        print("正在清空评测记录...")
        cursor.execute('DROP TABLE IF EXISTS eval_records')

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

    # 创建评测记录表（重构版，包含 Gem, Opus, GPT, Grok 四种评分模型）
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
            
            -- 评分与反馈 (五种评委，权重相同)
            eval_score REAL,                    -- 综合评分 (0-100)
            eval_comment TEXT,                  -- 综合评语
            
            eval_score_1 INTEGER,               -- 评委1 评分 (0-100)
            eval_comment_1 TEXT,                -- 评委1 评语
            eval_score_2 INTEGER,               -- 评委2 评分 (0-100)
            eval_comment_2 TEXT,                -- 评委2 评语
            eval_score_3 INTEGER,               -- 评委3 评分 (0-100)
            eval_comment_3 TEXT,                -- 评委3 评语
            eval_score_4 INTEGER,               -- 评委4 评分 (0-100)
            eval_comment_4 TEXT,                -- 评委4 评语
            eval_score_5 INTEGER,               -- 评委5 评分 (0-100)
            eval_comment_5 TEXT,                -- 评委5 评语
            
            -- 元数据
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            
            FOREIGN KEY (case_id) REFERENCES test_cases(id) ON DELETE CASCADE
        )
    ''')

    conn.commit()
    conn.close()
    print("数据库初始化成功！")
    print("   - test_cases 表已就绪")
    print("   - eval_records 表已更新为五模型架构")

if __name__ == "__main__":
    # 如果通过命令行运行且带有 --clear 参数，则清空记录
    clear_records = "--clear" in sys.argv
    init_db(clear_records=clear_records)
