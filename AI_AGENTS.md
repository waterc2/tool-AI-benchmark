# Local LLM Code Benchmarker

本地模型编程能力自动化测试工具

## 📖 项目简介

Local LLM Code Benchmarker 是一个用于自动化测试本地大语言模型代码生成能力的工具。通过管理真实的编程测试用例，系统可以批量执行测试并使用评委大模型进行智能评分和分析，帮助开发者客观评估和比较不同本地模型的编程表现。

## ✨ 核心功能

### 用例管理
- 创建、编辑和管理测试用例
- 支持多文件上下文的代码输入
- 自定义提示词和参考答案

### 批量测试
- 选择单个或多个用例进行批量测试
- 自动调用本地模型 API（默认地址: `http://10.0.0.114:8080/v1`）
- 实时捕获：代码回答、思维链内容、Token 数量、耗时、生成速度
- **异步执行**：测试完一个用例立即开始下一个，无需等待评分完成

### 智能评测
- 将模型回答与参考答案发送给评委大模型
- 获取 0-100 的评分和详细评价意见
- **三评委并行评分**：Super、High、Low 三个评委模型同时打分
- **异步评分队列**：评分任务在后台异步执行，不阻塞测试流程
- 支持多次测试结果对比和重新评分

### 数据分析
- 按模型查看平均分统计和各题详情 (平均分采用 Super 50%, High 30%, Low 20% 加权计算)
- 按测试题查看全模型平均分及排名
- 按平均耗时查看模型速度排行（耗时越短排名越高）
- 历史记录持久化存储

## 🛠️ 技术栈

- **Python** - 主要开发语言
- **Streamlit** - Web UI 界面
- **SQLite** - 数据持久化
- **LiteLLM/OpenAI SDK** - LLM API 调用
- **ThreadPoolExecutor** - 异步任务并发执行

## 📁 项目结构

```
tool-AI-benchmark/
├── app.py              # 主应用界面
├── database.py         # 数据库操作模块
├── init_db.py          # 数据库初始化
├── llm_client.py       # LLM API 客户端
├── AI_AGENTS.md        # 项目文档
├── README.md           # 运行指南
├── requirements.txt    # 依赖列表
└── eval_results.db     # SQLite 数据库
```

## 🚀 快速开始

### 环境要求

- Python 3.8+
- 本地 LLM 服务（如 Ollama、LM Studio 等）

### 安装依赖

```bash
pip install -r requirements.txt
```

### 配置说明

在 `.env` 文件中配置相关参数：

```env
# 本地模型 API 地址
LOCAL_MODEL_BASE_URL=http://10.0.0.114:8080/v1

# 评委模型 API 地址（可选）
JUDGE_MODEL_BASE_URL=https://api.openai.com/v1
JUDGE_MODEL_API_KEY=your-api-key
```

### 运行应用

```bash
streamlit run app.py
```

## 📊 数据库设计

### test_cases 表 - 测试用例表

| 字段 | 类型 | 说明 |
|------|------|------|
| id | INTEGER | 用例 ID |
| title | TEXT | 用例标题 |
| category | TEXT | 分类 |
| source_code | TEXT | 源代码（JSON 格式存储多文件） |
| prompt | TEXT | 修改要求提示词 |
| reference_answer | TEXT | 参考答案 |
| created_at | DATETIME | 创建时间 |

### eval_records 表 - 评测记录表

| 字段 | 类型 | 说明 |
|------|------|------|
| id | INTEGER | 记录 ID |
| case_id | INTEGER | 用例 ID（外键） |
| model_name | TEXT | 模型名称 |
| local_response | TEXT | 模型回答 |
| chain_of_thought | TEXT | 思维链内容 |
| prompt_tokens | INTEGER | 提示词 Token 数 |
| completion_tokens | INTEGER | 回答 Token 数 |
| total_time_ms | INTEGER | 总耗时（毫秒） |
| tokens_per_second | REAL | 生成速度 |
| eval_score | REAL | 评测分数 |
| eval_comment | TEXT | 评测意见 |
| created_at | DATETIME | 创建时间 |

## 📋 开发历程

### 第一阶段：数据库架构升级
- [x] 更新 `init_db.py`，创建 test_cases 表并重构 eval_records 表
- [x] 编写 `database.py`，实现用例的 CRUD 和记录的保存

### 第二阶段：API 客户端增强
- [x] 更新 `llm_client.py`，适配本地模型 URL
- [x] 实现思维链（CoT）提取逻辑（解析 `＜think＞` 标签）

### 第三阶段：UI 界面重构
- [x] 实现侧边栏导航（用例管理、执行测试、历史记录）
- [x] 开发用例管理界面，支持多文件代码输入
- [x] 开发批量测试界面，包含进度条和实时结果展示
- [x] 实现测试用例的编辑功能

### 第四阶段：完善与文档
- [x] 补充历史记录的详细对比视图
- [x] 更新 README.md 提供运行指南

### 第五阶段：统计与分析
- [x] 实现以模型为单位的平均分统计及各题详情
- [x] 实现以测试题为单位的全模型平均分统计及模型排名

### 第六阶段：性能优化
- [x] 实现本地模型测试与评分的异步执行架构
- [x] 三评委模型并行打分，减少评分耗时
- [x] 评分队列后台运行，测试流程不阻塞
- [x] 双进度条显示测试与评分进度

## ⚡ 异步执行架构

### 执行流程

```
用例1 → 本地模型测试 → 保存初始记录 → 提交评分任务(后台) → 立即开始用例2
                                              ↓ (异步并发)
                                         三评委并行评分
                                         (Super + High + Low)
                                              ↓
                                         更新数据库评分
```

### 性能优势

1. **测试与评分解耦**：本地模型测试完成后立即开始下一个用例，无需等待评分
2. **三评委并行**：Super、High、Low 三个评委同时执行，评分时间降低至原来的 1/3
3. **后台评分队列**：最多支持 3 个评分任务并发执行
4. **实时进度监控**：双进度条分别显示测试进度和评分进度

### 技术实现

- `BackgroundTaskManager`：管理异步测试和评分任务
- `ThreadPoolExecutor(max_workers=3)`：评分任务线程池
- `call_all_evaluators()`：并行调用三个评委模型
- `update_eval_scores()`：评分完成后更新数据库

## 📝 许可证

MIT License
